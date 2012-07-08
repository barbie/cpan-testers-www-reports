#!/usr/bin/perl
use strict;
$|++;

my $VERSION = '0.01';

#----------------------------------------------------------------------------

=head1 NAME

release-summary.cgi - program to return statistics of a CPAN distribution

=head1 SYNOPSIS

  perl release-summary.cgi

=head1 DESCRIPTION

Called in a CGI context, returns the current reporting statistics for a CPAN
distribution, depending upon the POST parameters provided.

=cut

# -------------------------------------
# Library Modules

use OpenThought();
use CGI;
use Config::IniFiles;
use CPAN::Testers::Common::DBUtils;
use Template;
use JSON;
use IO::File;
use Data::Dumper;

# -------------------------------------
# Variables

my $DEBUG = 1;

my $VHOST = '/var/www/reports/';
my (%options,%cgiparams,$cgi,%results);

my %rules = (
    dist    => qr/^([-\w.]+)$/i,
    version => qr/^([-\w.]+)$/i,
    oncpan  => qr/^([0-2])$/i,
    distmat => qr/^([0-2])$/i,
    perlmat => qr/^([0-2])$/i,
    patches => qr/^([0-2])$/i,
    perlver => qr/^([\w.]+)$/i,
    osname  => qr/^([\w.]+)$/i,
    format  => qr/^(text|ajax|json)$/i
);

my $EXCEPTIONS;
my %SYMLINKS;
my %MERGED;

# -------------------------------------
# Program

init_options();
process_dist()      if($cgiparams{dist});
process_response();

# -------------------------------------
# Subroutines

sub init_options {
    $options{config} = $VHOST . 'cgi-bin/config/settings.ini';

    error("Must specific the configuration file\n")             unless($options{config});
    error("Configuration file [$options{config}] not found\n")  unless(-f $options{config});

    # load configuration
    my $cfg = Config::IniFiles->new( -file => $options{config} );

    # configure DB
    my $db = 'CPANSTATS';
    my %opts = map {$_ => $cfg->val($db,lc $db . '_' . $_);} qw(driver database dbfile dbhost dbport dbuser dbpass);
    $options{$db} = CPAN::Testers::Common::DBUtils->new(%opts);
    error("Cannot configure '$options{database}' database\n")   unless($options{$db});

    #audit("DEBUG: configuration done: opts=".Dumper(\%opts));

    $cgi = CGI->new;

    for my $key (keys %rules) {
        my $val = $cgi->param($key);
        $cgiparams{$key} = $1   if($val =~ $rules{$key});
    }

    #audit('DEBUG: cgiparams=',Dumper(\%cgiparams));

    my $config = $VHOST . 'cgi-bin/config/cpan-config.ini';
    error("Must specific the configuration file\n")             unless($config);
    error("Configuration file [$config] not found\n")           unless(-f $config);

    $cfg = Config::IniFiles->new( -file => $config );

    if($cfg->SectionExists('EXCEPTIONS')) {
        my @values = $cfg->val('EXCEPTIONS','LIST');
        $EXCEPTIONS = join('|',@values);
    }

    if($cfg->SectionExists('SYMLINKS')) {
        $SYMLINKS{$_} = $cfg->val('SYMLINKS',$_)  for($cfg->Parameters('SYMLINKS'));
        push @{$MERGED{$SYMLINKS{$_}}}, $_              for(keys %SYMLINKS);
        push @{$MERGED{$SYMLINKS{$_}}}, $SYMLINKS{$_}   for(keys %SYMLINKS);
    }

    #audit('DEBUG: SYMLINKS=',Dumper(\%SYMLINKS));
    #audit('DEBUG: MERGED=',Dumper(\%MERGED));

    #$cgiparams{dist} = 'App-Maisha';
    #$cgiparams{format} = 'ajax';
}

sub process_dist {
    $cgiparams{dist} = $SYMLINKS{$cgiparams{dist}}  if(defined $SYMLINKS{$cgiparams{dist}});

    if($cgiparams{osname} || $cgiparams{perlver}) {
        process_dist_long();
    } else {
        process_dist_short();
    }
}

sub process_dist_short {
    audit("DEBUG: start process dist (short): $cgiparams{dist}");

    my @where;
    push @where, "patched=$cgiparams{patches}"      if($cgiparams{patches});
    push @where, "distmat=$cgiparams{distmat}"      if($cgiparams{distmat});
    push @where, "perlmat=$cgiparams{perlmat}"      if($cgiparams{perlmat});
    push @where, "oncpan=$cgiparams{oncpan}"        if($cgiparams{oncpan});
    my $where = @where ? ' AND ' . join(' AND ',@where) : '';

    my $dist = "'$cgiparams{dist}'";
    $dist = "'" . join("','",@{$MERGED{$cgiparams{dist}}}) . "'"    if(defined $MERGED{$cgiparams{dist}});
    my $sql = "SELECT version,sum(pass) as pass, sum(fail) as fail, sum(na) as na, sum(unknown) as unknown FROM release_summary" .
    	" WHERE dist IN ($dist) $where GROUP BY version ORDER BY version";

    audit("DEBUG: sql=$sql");

    my $next = $options{CPANSTATS}->iterator('hash', $sql );

    my ( $summary );
    while ( my $row = $next->() ) {
        next unless $row->{version};

        $summary->{ $row->{version} }->{ PASS }    = $row->{pass};
        $summary->{ $row->{version} }->{ FAIL }    = $row->{fail};
        $summary->{ $row->{version} }->{ NA }      = $row->{na};
        $summary->{ $row->{version} }->{ UNKNOWN } = $row->{unknown};
        $summary->{ $row->{version} }->{ ALL }     = $row->{pass} + $row->{fail} + $row->{na} + $row->{unknown};
    }

    audit("DEBUG: summary=".Dumper($summary));

    my $oncpan = q!'cpan','upload','backpan'!;
    $oncpan = q!'cpan','upload'!    if($cgiparams{oncpan} && $cgiparams{oncpan} == 1);
    $oncpan = q!'backpan'!          if($cgiparams{oncpan} && $cgiparams{oncpan} == 2);

    # ensure we cover all known versions
    my @rows = $options{CPANSTATS}->get_query(
                    'array',
                    "SELECT DISTINCT(version) FROM uploads WHERE dist IN ($dist) AND type IN ($oncpan) ORDER BY released DESC" );
    my @versions;
    for(@rows) {
        next    if($cgiparams{distmat} && $cgiparams{distmat} == 1     && $_->[0]  =~ /_/i);
        next    if($cgiparams{distmat} && $cgiparams{distmat} == 2     && $_->[0]  !~ /_/i);
        push @versions, $_->[0];
    }

    %results = (
        versions    => \@versions,
        summary     => $summary,
    );
}

sub process_dist_long {
    audit("DEBUG: start process dist (long): $cgiparams{dist}");

    my @where;
    push @where, "(perl NOT LIKE '%patch%' AND perl NOT LIKE '%RC%')"   if($cgiparams{patches} && $cgiparams{patches} == 1);
    push @where, "(perl LIKE '%patch%' OR perl LIKE '%RC%')"            if($cgiparams{patches} && $cgiparams{patches} == 2);
    push @where, "version NOT LIKE '%\\_%'"     if($cgiparams{distmat} && $cgiparams{distmat} == 1);
    push @where, "version LIKE '%\\_%'"         if($cgiparams{distmat} && $cgiparams{distmat} == 2);
    #push @where, "perl NOT REGEX '^5.(7|9|11)'" if($cgiparams{perlmat} && $cgiparams{perlmat} == 1);
    #push @where, "perl REGEX '^5.(7|9|11)'"     if($cgiparams{perlmat} && $cgiparams{perlmat} == 2);
    my $where = @where ? ' AND ' . join(' AND ',@where) : '';

    my $dist = "'$cgiparams{dist}'";
    $dist = "'" . join("','",@{$MERGED{$cgiparams{dist}}}) . "'"    if(defined $MERGED{$cgiparams{dist}});
    my $sql = "SELECT id, state, version, perl, osname, FROM cpanstats WHERE dist IN ($dist) AND state != 'cpan' $where ORDER BY version, id";

    #audit("DEBUG: sql=$sql");

    my $next = $options{CPANSTATS}->iterator('hash', $sql );

    my ( $summary );
    while ( my $row = $next->() ) {
        next unless $row->{version};
        $row->{perl} = "5.004_05" if $row->{perl} eq "5.4.4"; # RT 15162
        #next    if($cgiparams{patches} && $cgiparams{patches} == 1     && $row->{perl}     =~ /(patch|RC)/i);
        #next    if($cgiparams{patches} && $cgiparams{patches} == 2     && $row->{perl}     !~ /(patch|RC)/i);
        #next    if($cgiparams{distmat} && $cgiparams{distmat} == 1     && $row->{version}  =~ /_/i);
        #next    if($cgiparams{distmat} && $cgiparams{distmat} == 2     && $row->{version}  !~ /_/i);
        next    if($cgiparams{perlmat} && $cgiparams{perlmat} == 1     && $row->{perl}     =~ /^5.(7|9|11)/);
        next    if($cgiparams{perlmat} && $cgiparams{perlmat} == 2     && $row->{perl}     !~ /^5.(7|9|11)/);
        next    if($cgiparams{perlver} && $cgiparams{perlver} ne 'ALL' && $row->{perl}     !~ /$cgiparams{perlver}/i);
        next    if($cgiparams{osname}  && $cgiparams{osname}  ne 'ALL' && $row->{osname}   !~ /$cgiparams{osname}/i);

        $summary->{ $row->{version} }->{ uc $row->{state} }++;
        $summary->{ $row->{version} }->{ 'ALL' }++;
    }

    #audit("DEBUG: summary=".Dumper($summary));

    my $oncpan = q!'cpan','upload','backpan'!;
    $oncpan = q!'cpan','upload'!    if($cgiparams{oncpan} && $cgiparams{oncpan} == 1);
    $oncpan = q!'backpan'!          if($cgiparams{oncpan} && $cgiparams{oncpan} == 2);

    # ensure we cover all known versions
    my @rows = $options{CPANSTATS}->get_query(
                    'array',
                    "SELECT DISTINCT(version) FROM uploads WHERE dist IN ($dist) AND type IN ($oncpan) ORDER BY released DESC" );
    my @versions;
    for(@rows) {
        next    if($cgiparams{distmat} && $cgiparams{distmat} == 1     && $_->[0]  =~ /_/i);
        next    if($cgiparams{distmat} && $cgiparams{distmat} == 2     && $_->[0]  !~ /_/i);
        push @versions, $_->[0];
    }

    %results = (
        versions    => \@versions,
        summary     => $summary,
    );
}

sub process_response {

    audit("DEBUG: results=".Dumper(\%results));

    if($cgiparams{format} eq 'ajax') {
        my $ot = OpenThought->new();
        my $tt = Template->new(
            {
                #    POST_CHOMP => 1,
                #    PRE_CHOMP => 1,
                #    TRIM => 1,
                EVAL_PERL    => 1,
                INCLUDE_PATH => [ 'templates' ],
            }
        );

        my $str;
        $tt->process( 'dist_summary.html', \%results, \$str )
                || error( $tt->error );

        #audit("DEBUG: str=$str");
        audit("DEBUG: end process dist: $cgiparams{dist}");

        my $html;
        $html->{'reportsummary'} = $str;
        $ot->param( $html );

        #audit("DEBUG: response=" . $ot->response());

        print $cgi->header;
        print $ot->response();
        print "\n";
    } elsif($cgiparams{format} eq 'json') {
        print "Content-Type: text/xml; charset=ISO-8859-1\n";
        print "Cache-Control: no-cache\n\n";
        if(%results) {
            my @json;
            for my $vers (@{$results{versions}}) {
                push @json, { version => $vers, map {uc $_ => $results{summary}{$vers}{uc $_}} qw(pass fail na unknown all) };
            }

            print encode_json(\@json);
        }

    } elsif(%results) {
        print( "Content-Type: text/text; charset=ISO-8859-1\n" );
        print( "Cache-Control: no-cache\n\n" );
        if(%results) {
            for my $vers (@{$results{versions}}) {
                printf "%s,%d,%d,%d,%d,%d\n", $vers, map {$results{summary}{$vers}{uc $_}} qw(pass fail na unknown all);
            }
        }

    } else {
        print( "Content-Type: text/text; charset=ISO-8859-1\n" );
        print( "Cache-Control: no-cache\n\n" );
    }
}

sub error {
    audit('ERROR:',@_);
    print STDERR @_;
    print $cgi->header('text/plain'), "Error retrieving data\n";
    exit;
}

sub audit {
    return  unless($DEBUG);

    my @date = localtime(time);
    my $date = sprintf "%04d/%02d/%02d %02d:%02d:%02d", $date[5]+1900, $date[4]+1, $date[3], $date[2], $date[1], $date[0];

    my $fh = IO::File->new($VHOST . 'cgi-bin/cache/summary-audit.log','a+') or return;
    print $fh "$date " . join(' ',@_ ). "\n";
    $fh->close;
}

1;

__END__

=head1 BUGS, PATCHES & FIXES

There are no known bugs at the time of this release. However, if you spot a
bug or are experiencing difficulties, that is not explained within the POD
documentation, please send bug reports and patches to the RT Queue (see below).

Fixes are dependant upon their severity and my availablity. Should a fix not
be forthcoming, please feel free to (politely) remind me.

RT: http://rt.cpan.org/Public/Dist/Display.html?Name=CPAN-WWW-Testers

=head1 SEE ALSO

L<CPAN::WWW::Testers::Generator>
L<CPAN::Testers::WWW::Statistics>

F<http://www.cpantesters.org/>,
F<http://stats.cpantesters.org/>

=head1 AUTHOR

  Barbie       <barbie@cpan.org>   2010

=head1 COPYRIGHT AND LICENSE

  Copyright (C) 2010 Barbie <barbie@cpan.org>

  This module is free software; you can redistribute it and/or
  modify it under the same terms as Perl itself.

=cut
