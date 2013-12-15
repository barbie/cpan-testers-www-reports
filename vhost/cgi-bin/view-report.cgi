#!/usr/bin/perl
use strict;
$|++;

my $VERSION = '3.44';

#----------------------------------------------------------------------------

=head1 NAME

view-report.cgi - program to display a individual CPAN Testers report.

=head1 SYNOPSIS

  perl view-report.cgi

=head1 DESCRIPTION

Called in a CGI context, returns the specified CPAN Testers report.

=cut

# -------------------------------------
# Library Modules

use lib qw(lib plugins);

use Labyrinth;
use Labyrinth::Audit;
use Labyrinth::DBUtils;
use Labyrinth::Globals  qw(:all);
use Labyrinth::MLUtils;
use Labyrinth::Variables;
use Labyrinth::Writer;

use Labyrinth::Plugin::CPAN;

#use CGI::Carp			qw(fatalsToBrowser);

use CGI;
use Config::IniFiles;
use Data::Dumper;
use Data::FlexSerializer;
use IO::File;
use JSON;
use MIME::QuotedPrint;
use Template;
use Text::Demoroniser qw(demoroniser);

use CPAN::Testers::Common::Article;
use CPAN::Testers::Common::Utils qw(nntp_to_guid guid_to_nntp);
use CPAN::Testers::Fact::LegacyReport;
use CPAN::Testers::Fact::TestSummary;

# -------------------------------------
# Variables

my $DEBUG = 0;
my $LONG_ALLOWED = 0;

my $VHOST = '/var/www/reports/';
my (%options,$serializer,$logfile);

my $EXCEPTIONS;
my %SYMLINKS;
my %MERGED;

# -------------------------------------
# Program

init_options();
process_report();

# -------------------------------------
# Subroutines

sub init_options {
    $options{config} = $VHOST . 'cgi-bin/config/settings.ini';

    error("Must specific the configuration file\n")             unless($options{config});
    error("Configuration file [$options{config}] not found\n")  unless(-f $options{config});

    $serializer = Data::FlexSerializer->new(
        detect_compression => 1,
    );

    # load configuration
    Labyrinth::Variables::init();   # initial standard variable values
    LoadSettings($options{config});            # Load All Global Settings

    $logfile = $settings{'logfile'} . '.reports';

    SetLogFile( FILE   => $logfile,
                USER   => 'labyrinth',
                LEVEL  => ($settings{'loglevel'} || 0),
                CLEAR  => 1,
                CALLER => 1);

    ParseParams();
    DBConnect();

    ## defaults in the event of errors
    my $LAYOUT = 'public/layout.html';
    $tvars{layout} = $LAYOUT;
    $tvars{content} = '';

    LogDebug("DEBUG: configuration done");

#    for my $key (keys %rules) {
#        my $val = $cgi->param("${key}_pref");
#        $cgiparams{$key} = $1   if($val =~ $rules{$key});
#    }

    LogDebug('DEBUG: cgiparams=',Dumper(\%cgiparams));
}

sub process_report {
    retrieve_report();
    print_report();
}

sub retrieve_report {
    if($cgiparams{id} =~ /^\d+$/) {
        my @rows = $dbi->GetQuery('hash','GetStatReport',$cgiparams{id});
        if(@rows) {
            if($rows[0]->{guid} =~ /^[0-9]+\-[-\w]+$/) {
                my $id = guid_to_nntp($rows[0]->{guid});
                _parse_nntp_report($id);
            } else {
                $cgiparams{id} = $rows[0]->{guid};
                _parse_guid_report();
            }
        } else {
            #$tvars{errcode} = 'NEXT';
            #$tvars{command} = 'cpan-distunk';
        }
   } elsif($cgiparams{id} =~ /^[\w-]+$/) {
        my $id = guid_to_nntp($cgiparams{id});
        if($id) {
            _parse_nntp_report($id);
        } else {
          _parse_guid_report();
        }
    } else {
        $cgiparams{id} =~ s/[\w-]+//g;
    }

    unless($tvars{article}{article}) {
        if($cgiparams{id} =~ /^\d+$/) {
            $tvars{article}{id} = $cgiparams{id};
        } else {
            $tvars{article}{guid} = $cgiparams{id};
        }
    }

    if($cgiparams{raw}) {
        $tvars{article}{raw} = $cgiparams{raw};
        $tvars{layout} = 'public/popup.html'
    } else {
        $tvars{layout} = 'public/layout-wide.html'
    }
}

sub print_report {
    $tvars{content}     = 'cpan/report-view.html';
    $tvars{siteversion} = $VERSION;
    $tvars{labversion}  = $Labyrinth::VERSION;
    Publish();
}

#----------------------------------------------------------------------------
# Private Interface Functions

sub _parse_nntp_report {
    my $nntpid = shift;
    my @rows;

LogDebug("parse nntp report: 1.nntp=$nntpid / $cgiparams{id}");

    unless($nntpid) {
       @rows = $dbi->GetQuery('hash','GetStatReport',$cgiparams{id});
       return  unless(@rows);
       $nntpid = guid_to_nntp($rows[0]->{guid});
    }

    @rows = $dbi->GetQuery('hash','GetArticle',$nntpid);
       return  unless(@rows);

    if($rows[0]->{article} =~ /Content-Transfer-Encoding: quoted-printable/is) {
        my ($head,$body) = split(/\n\n/,$rows[0]->{article},2);
        $body = decode_qp($body);
        $rows[0]->{article} = $head . "\n\n" . $body;
    }

    $rows[0]->{article} = demoroniser($rows[0]->{article});
    $rows[0]->{article} = SafeHTML($rows[0]->{article});
    $tvars{article} = $rows[0];
    ($tvars{article}{head},$tvars{article}{body}) = split(/\n\n/,$rows[0]->{article},2);

    my $object = CPAN::Testers::Common::Article->new($rows[0]->{article});
    return  unless($object);

    $tvars{article}{nntp}    = 1;
    $tvars{article}{id}      = $cgiparams{id};
    $tvars{article}{body}    = $object->body;
    $tvars{article}{subject} = $object->subject;
    $tvars{article}{from}    = $object->from;
    $tvars{article}{from}    =~ s/\@.*//;
    $tvars{article}{post}    = $object->postdate;

    my @date = $object->date =~ /^(\d{4})(\d{2})(\d{2})(\d{2})(\d{2})/;
    $tvars{article}{date}    = sprintf "%04d-%02d-%02dT%02d:%02d:00Z", @date;

    return      if($tvars{article}{subject} =~ /Re:/i);
    return      unless($tvars{article}{subject} =~ /(CPAN|FAIL|PASS|NA|UNKNOWN)\s+/i);

    my $state = lc $1;

    if($state eq 'cpan') {
        if($object->parse_upload()) {
            $tvars{article}{dist}    = $object->distribution;
            $tvars{article}{version} = $object->version;
            $tvars{article}{author}  = $object->author;
            $tvars{article}{letter}  = substr($tvars{article}{dist},0,1);
        }
    } else {
        if($object->parse_report()) {
            $tvars{article}{dist}    = $object->distribution;
            $tvars{article}{version} = $object->version;
            $tvars{article}{author}  = $object->from;
            $tvars{article}{letter}  = substr($tvars{article}{dist},0,1);
        }
    }
}

sub _parse_guid_report {
    my $cpan = Labyrinth::Plugin::CPAN->new();
    $cpan->Configure();

LogDebug("parse guid report: $cgiparams{id}");

    my @rows = $dbi->GetQuery('hash','GetMetabaseByGUID',$cgiparams{id});
    return  unless(@rows);

    my $data = $serializer->deserialize($rows[0]->{report});
    #my $data = decode_json($rows[0]->{report});

LogDebug("data: ".Dumper($data));

    my $fact;
    eval { $fact = CPAN::Testers::Fact::LegacyReport->from_struct( $data->{'CPAN::Testers::Fact::LegacyReport'} ) };
    if($@ && !$fact) {
        error('LegacyReport',$@);
        return;
    }

    $tvars{article}{article}    = SafeHTML($fact->{content}{textreport});
    #$tvars{article}{id}         = $rows[0]->{id};
    $tvars{article}{guid}       = $rows[0]->{guid};

    my $report;
    eval { $report = CPAN::Testers::Fact::TestSummary->from_struct( $data->{'CPAN::Testers::Fact::TestSummary'} ) };
    if($@ && !$report) {
        error('TestSummary',$@);
        return;
    }

    my ($osname) = $cpan->OSName($report->{content}{osname});

    $tvars{article}{state}      = lc $report->{content}{grade};
    $tvars{article}{platform}   = $report->{content}{archname};
    $tvars{article}{osname}     = $osname;
    $tvars{article}{osvers}     = $report->{content}{osversion};
    $tvars{article}{perl}       = $report->{content}{perl_version};
    $tvars{article}{created}    = $report->{metadata}{core}{creation_time};

    my $dist                    = Metabase::Resource->new( $report->{metadata}{core}{resource} );
    $tvars{article}{dist}       = $dist->metadata->{dist_name};
    $tvars{article}{version}    = $dist->metadata->{dist_version};

    ($tvars{article}{author},$tvars{article}{from}) = get_tester( $report->creator );
    $tvars{article}{author} =~ s/\@/ [at] /g;
    $tvars{article}{from}   =~ s/\@/ [at] /g;
    $tvars{article}{from}   =~ s/\./ [dot] /g;

    if($tvars{article}{created}) {
        my @created = $tvars{article}{created} =~ /(\d+)-(\d+)-(\d+)T(\d+):(\d+):(\d+)Z/; # 2010-02-23T20:33:52Z
        $tvars{article}{postdate}   = sprintf "%04d%02d", $created[0], $created[1];
        $tvars{article}{fulldate}   = sprintf "%04d%02d%02d%02d%02d", $created[0], $created[1], $created[2], $created[3], $created[4];
    } else {
        my @created = localtime(time);
        $tvars{article}{postdate}   = sprintf "%04d%02d", $created[5]+1900, $created[4]+1;
        $tvars{article}{fulldate}   = sprintf "%04d%02d%02d%02d%02d", $created[5]+1900, $created[4]+1, $created[3], $created[2], $created[1];
    }

    $tvars{article}{letter}  = substr($tvars{article}{dist},0,1);

    $tvars{article}{subject} = sprintf "%s %s-%s %s %s", 
        uc $tvars{article}{state}, $tvars{article}{dist}, $tvars{article}{version}, $tvars{article}{perl}, $tvars{article}{osname};
}

sub get_tester {
    my $creator = shift;

    #$dbi->{'mysql_enable_utf8'} = 1;
    my @rows = $dbi->GetQuery('hash','GetTesterFact',$creator);
    return ($creator,$creator)  unless(@rows);

    #$rows[0]->{fullname} = encode_entities($rows[0]->{fullname});
    $rows[0]->{email} ||= $creator;
    $rows[0]->{email} =~ s/\'/''/g if($rows[0]->{email});
    return ($rows[0]->{fullname},$rows[0]->{email});
}

sub error {
    LogError('ERROR:',@_);
    print STDERR @_;
    print $cgi->header('text/plain'), "Error retrieving data\n";
    exit;
}

1;

__END__

=head1 BUGS, PATCHES & FIXES

There are no known bugs at the time of this release. However, if you spot a
bug or are experiencing difficulties, that is not explained within the POD
documentation, please send bug reports and patches to the RT Queue (see below).

Fixes are dependant upon their severity and my availablity. Should a fix not
be forthcoming, please feel free to (politely) remind me.

RT: http://rt.cpan.org/Public/Dist/Display.html?Name=CPAN-Testers=WWW-Reports

=head1 SEE ALSO

L<CPAN::Testers::WWW::Statistics>,
L<CPAN::Testers::WWW::Wiki>,
L<CPAN::Testers::WWW::Blog>

F<http://www.cpantesters.org/>,
F<http://stats.cpantesters.org/>,
F<http://wiki.cpantesters.org/>,
F<http://blog.cpantesters.org/>

=head1 AUTHOR

  Barbie       <barbie@cpan.org>   2008-present

=head1 COPYRIGHT AND LICENSE

  Copyright (C) 2008-2013 Barbie <barbie@cpan.org>

  This module is free software; you can redistribute it and/or
  modify it under the Artistic License 2.0.

=cut
