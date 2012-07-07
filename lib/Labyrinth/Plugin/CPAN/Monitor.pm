package Labyrinth::Plugin::CPAN::Monitor;

use strict;
use warnings;

use vars qw($VERSION);
$VERSION = '3.36';

=head1 NAME

Labyrinth::Plugin::CPAN::Monitor - Plugin to monitor actions and tables

=cut

#----------------------------------------------------------------------------
# Libraries

use base qw(Labyrinth::Plugin::Base);

use Labyrinth::Audit;
use Labyrinth::DTUtils;
use Labyrinth::Variables;

use Labyrinth::Plugin::CPAN;

use GD::Graph::lines;
use GD::Graph::colour qw(:colours :convert);
use WWW::Mechanize;

#----------------------------------------------------------------------------
# Variables

my $HOURS24 = 60 * 60 * 24;
my $WEEKS1  = 60 * 60 * 24 * 7;
my $WEEKS4  = 60 * 60 * 24 * 7 * 4;

my $mech = WWW::Mechanize->new();
$mech->agent_alias( 'Linux Mozilla' );

my $chart_api    = 'http://chart.apis.google.com/chart?chs=640x300&cht=lc';
my $chart_titles = 'chtt=%s&chdl=%s';
my $chart_labels = 'chxt=x,x,y,r&chxl=0:|%s|1:|%s|2:|%s|3:|%s';
my $chart_data   = 'chd=t:%s';
my $chart_colour = 'chco=%s';
my $chart_filler = 'chf=bg,s,dddddd';

my %COLOURS = (
    white      => 'FFFFFF',
    black      => '000000',
    red        => 'FF0000',
    blue       => '0000FF',
    green      => '00FF00',
    orange     => 'E76300',
    purple     => '800080',
    cyan       => '00FFFF',
    cream      => 'C8C8F0',
    yellow     => 'FFFF00',
    brown      => '987654',
    violet     => '8A2BE2',
    torch      => 'FD0E35',
);

# predefine colours in GD::Chart::colours:
#   white, lgray, gray, dgray, black, lblue, blue, dblue, gold, lyellow, yellow, 
#   dyellow, lgreen, green, dgreen, lred, red, dred, lpurple, purple, dpurple, 
#   lorange, orange, pink, dpink, marine, cyan, lbrown, dbrown.

#my @COLOURS = qw(violet blue cyan green orange red torch brown cream yellow purple);
my @COLOURS = qw(purple blue cyan green orange red dred brown cream yellow dpurple);
#my @COLOURS = map {$COLOURS{$_}} qw(violet blue cyan green orange red torch brown cream yellow purple);

#----------------------------------------------------------------------------
# Public Interface Functions

=head1 METHODS

=head2 Public Interface Methods

=over 4

=item Snapshot

Generate a new snapshot in the database.

=item Graphs

Provide monitor graphs

=back

=cut

sub Snapshot {
    my ($self,$progress) = @_;
    $progress->( "Create START" )   if(defined $progress);

    my @rows = $dbi->GetQuery('array','CountRequests');
    my $sql  = $rows[0]->[0] > 0 ? 'CreateSnapshot' : 'CreateSnapshot0';
    my $next = $dbi->Iterator('array',$sql);
    while(my $row = $next->()) {
        $dbi->DoQuery('InsertSnapshot',@$row);
    }

    $progress->( "Create STOP" )    if(defined $progress);
}

sub Graphs {
    my ($self,$progress) = @_;
    $progress->( "Update START" )   if(defined $progress);

    my @date = localtime(time - $HOURS24);
    my $timestamp = sprintf "%04d-%02d-%02d %02d:%02d:%02d",
        $date[5]+1900,$date[4]+1,$date[3],$date[2],$date[1],$date[0];

    my (%data,%days);
    my @rows = $dbi->GetQuery('hash','GetSnapshots',{timestamp => $timestamp});
    for my $row (@rows) {
        my $date = sprintf "%04d%02d%02d", $row->{year}, $row->{month}, $row->{day};
        $data{$row->{now}}{$date} = $row;
        $days{$date} = sprintf "%02d/%02d/%04d", $row->{day}, $row->{month}, $row->{year};;
    }

    _make_graphs(\%days,\%data,'-1d',$progress);

    @date = localtime(time - $WEEKS1);
    $timestamp = sprintf "%04d-%02d-%02d %02d:%02d:%02d",
        $date[5]+1900,$date[4]+1,$date[3],$date[2],$date[1],$date[0];

    (%data,%days) = ();
    @rows = $dbi->GetQuery('hash','GetSnapshots',{timestamp => $timestamp});
    for my $row (@rows) {
        my $date = sprintf "%04d%02d%02d", $row->{year}, $row->{month}, $row->{day};
        $data{$row->{now}}{$date} = $row;
        $days{$date} = sprintf "%02d/%02d/%04d", $row->{day}, $row->{month}, $row->{year};;
    }

    my $r = 0;
    for my $d (keys %data) {
        next    if($r++ % 4 == 0);
        delete $data{$d};
    }

    _make_graphs(\%days,\%data,'-1w',$progress);
}

#----------------------------------------------------------------------------
# Private Interface Functions

sub _make_graphs {
    my ($days,$data,$suffix,$progress) = @_;

    my $y = 0;
    my (@name_count,@page_count,@page_weight,%seen);
    my ($max_name_count,$max_page_count,$max_page_weight) = (0,0,0);
    for my $now (sort keys %$data) {
        my (@now) = $now =~ /(\d+)-(\d+)-(\d+) (\d+):(\d+):(\d+)/;
        if($suffix eq '-1d') {
            push @{ $name_count[0]  }, $y % 4 == 0 ? "$4:$5" : '';
            push @{ $page_count[0]  }, $y % 4 == 0 ? "$4:$5" : '';
            push @{ $page_weight[0] }, $y % 4 == 0 ? "$4:$5" : '';
        } else {
            push @{ $name_count[0]  }, !$seen{"$3/$2"} ? "$3/$2" : '';
            push @{ $page_count[0]  }, !$seen{"$3/$2"} ? "$3/$2" : '';
            push @{ $page_weight[0] }, !$seen{"$3/$2"} ? "$3/$2" : '';
            $seen{"$3/$2"} = 1;
        }
        $y++;

        my $inx = 1;
        for my $day (sort {$b <=> $a} keys %$days) {
            if(defined $data->{$now}{$day}) {
                push @{ $name_count[$inx]  }, $data->{$now}{$day}->{name_count};
                push @{ $page_count[$inx]  }, $data->{$now}{$day}->{page_count};
                push @{ $page_weight[$inx] }, $data->{$now}{$day}->{page_weight};

                $max_name_count  = $data->{$now}{$day}->{name_count}  if($max_name_count  < $data->{$now}{$day}->{name_count});
                $max_page_count  = $data->{$now}{$day}->{page_count}  if($max_page_count  < $data->{$now}{$day}->{page_count});
                $max_page_weight = $data->{$now}{$day}->{page_weight} if($max_page_weight < $data->{$now}{$day}->{page_weight});
            } else {
                push @{ $name_count[$inx]  }, 0;
                push @{ $page_count[$inx]  }, 0;
                push @{ $page_weight[$inx] }, 0;
            }
            $inx++;
        }
    }
    
    _write_image($max_name_count, 'Unique Page Requests',$days,\@name_count, "name_count$suffix", $progress);
    _write_image($max_page_count, 'Total Page Requests', $days,\@page_count, "page_count$suffix", $progress);
    _write_image($max_page_weight,'Total Page Weight',   $days,\@page_weight,"page_weight$suffix",$progress);

    $progress->( "Update STOP" )    if(defined $progress);
}

sub _write_image {
    my ($m,$title,$days,$data,$filename,$progress) = @_;
    my $max     = _set_max($m);
    my $range   = _set_range(0,$max);

    use Data::Dumper;
    $progress->( "DATA = [".(scalar(@$data))."] ".Dumper($data) )      if(defined $progress);

    #my $grey = add_colour(grey => hex2rgb('#eeeeee'));
    my $graph = GD::Graph::lines->new(640, 300);
    #add_colour($_ => hex2rgb($COLOURS{$_}))  for(@COLOURS);

    $graph->set(
        title               => $title,

        x_label             => 'Timestamp',
        x_label_position    => 0.5,
        x_labels_vertical   => 1,
        x_label_skip        => $filename =~ /-1d$/ ? 1 : 1,
        x_tick_length       => -2,

        y_label             => '',
        y_max_value         => $max,
        y_tick_length       => -2,
        y_number_format     => \&_y_format,

        line_width          => 2,
        axis_space          => 4,

        legend_placement    => 'RC',
        #dclrs               => [qw(lpurple blue cyan green orange red dred lbrown pink yellow dpurple)],
        dclrs               => [@COLOURS],
        boxclr              => '#eeeeee',
        labelclr            => 'dgray',
        axislabelclr        => 'dgray',
        legendclr           => 'dgray',
        valuesclr           => 'dgray',
        textclr             => 'dgray'
        
    ) or die $graph->error;
    my @days = map {$days->{$_}} sort {$b <=> $a} keys %$days;
    $graph->set_legend(@days);

    #my $font = '/usr/share/fonts/truetype/ttf-dejavu/DejaVuSans.ttf';
    my $font = '/usr/share/fonts/truetype/freefont/FreeSans.ttf';

    $graph->set_title_font(  $font,10);
    $graph->set_legend_font( $font,10);
    $graph->set_x_label_font($font,8);
    $graph->set_y_label_font($font,8);
    $graph->set_x_axis_font( $font,8);
    $graph->set_y_axis_font( $font,8);
    $graph->set_values_font( $font,8);


    my $gd = $graph->plot($data) or die $graph->error;

    my $file = "$settings{webdir}/static/$filename.png";
    my $fh = IO::File->new($file, 'w+') or die "Couldn't write to file [$file]: $!\n";
    binmode $fh;
    print $fh $gd->png;
    $fh->close;
}



sub _make_graphsX {
    my ($days,$data,$suffix,$progress) = @_;

    my $y = 0;
    my (@name_count,@page_count,@page_weight);
    my ($max_name_count,$max_page_count,$max_page_weight) = (0,0,0);
    for my $now (sort keys %$data) {
        my (@now) = $now =~ /(\d+)-(\d+)-(\d+) (\d+):(\d+):(\d+)/;
        if($y++ % 4 == 0) {
            push @{ $name_count[0]  }, $now[3];
            push @{ $page_count[0]  }, $now[3];
            push @{ $page_weight[0] }, $now[3];
            push @{ $name_count[1]  }, $now[4];
            push @{ $page_count[1]  }, $now[4];
            push @{ $page_weight[1] }, $now[4];
        } else {
            push @{ $name_count[0]  }, '';
            push @{ $page_count[0]  }, '';
            push @{ $page_weight[0] }, '';
            push @{ $name_count[1]  }, '';
            push @{ $page_count[1]  }, '';
            push @{ $page_weight[1] }, '';
        }
        my $inx = 2;
        for my $day (sort {$a <=> $b} keys %$days) {
            if(defined $data->{$now}{$day}) {
                push @{ $name_count[$inx]  }, $data->{$now}{$day}->{name_count};
                push @{ $page_count[$inx]  }, $data->{$now}{$day}->{page_count};
                push @{ $page_weight[$inx] }, $data->{$now}{$day}->{page_weight};

                $max_name_count  = $data->{$now}{$day}->{name_count}  if($max_name_count  < $data->{$now}{$day}->{name_count});
                $max_page_count  = $data->{$now}{$day}->{page_count}  if($max_page_count  < $data->{$now}{$day}->{page_count});
                $max_page_weight = $data->{$now}{$day}->{page_weight} if($max_page_weight < $data->{$now}{$day}->{page_weight});
            } else {
                push @{ $name_count[$inx]  }, 0;
                push @{ $page_count[$inx]  }, 0;
                push @{ $page_weight[$inx] }, 0;
            }
            $inx++;
        }
    }
    
    _write_image($max_name_count, 'Unique Page Requests',$days,\@name_count, "name_count$suffix", $progress);
    _write_image($max_page_count, 'Total Page Requests', $days,\@page_count, "page_count$suffix", $progress);
    _write_image($max_page_weight,'Total Page Weight',   $days,\@page_weight,"page_weight$suffix",$progress);

    $progress->( "Update STOP" )     if(defined $progress);
}

sub _write_imageX {
    my ($m,$title,$days,$data,$filename,$progress) = @_;
    #use Data::Dumper;
    #$progress->( "DATA = [".(scalar(@$data))."] ".Dumper($data) )      if(defined $progress);
    my $url = _make_graph_url($m,$title,$days,$data);
    $progress->( "URL = [".(length($url))."] $url" )    if(defined $progress);

    eval { $mech->get($url); };

    if($@ || !$mech->success()) {
        my $file = "$settings{webdir}/static/$filename.html";
        warn("FAIL: $0 - Cannot access page - see '$file'\n");
        $mech->save_content($file);
    } elsif($mech->response->header('Content-Type') =~ /html/) {
        my $file = "$settings{webdir}/static/$filename.html";
        warn("FAIL: $0 - request failed - see '$file'\n");
        $mech->save_content($file);
    } else {
        my $file = "$settings{webdir}/static/$filename.png";
        my $fh = IO::File->new(">$file") or die "$0 - Cannot write file [$file]: $!\n";
        binmode($fh);
        print $fh $mech->content;
        $fh->close;
    }
}

sub _make_graph_url {
    my ($m,$title,$days,$data) = @_;
    my $max     = _set_max($m);
    my $range   = _set_range(0,$max);

    my (@d,@c,@l);
    my @colours = @COLOURS;
    for my $inx (3 .. scalar(@$data)) {
        # data needs to be expressed as a percentage of the max
        for(@{$data->[$inx-1]}) {
            #print "pcent = $_ / $max * 100 = ";
            $_ = $_ / $max * 100;
            #print "$_ = ";
            $_ = int($_ * 1) / 1;
            #print "$_\n";
        }

        push @c, shift @colours;
        push @d, join(',',@{$data->[$inx-1]});
        push @l, ($inx-3) . ' day' . ($inx-3==1 ? '' : 's') . ' old';
    }

    @l = map {$days->{$_}} sort {$b <=> $a} keys %$days;

    my $xaxis1 = join('|', @{$data->[0]});
    my $xaxis2 = join('|', @{$data->[1]});
    my $datum  = sprintf $chart_data, join('|',reverse @d);
    my $colour = sprintf $chart_colour, join(',',@c);
    my $titles = sprintf $chart_titles, $title, join('|',@l);
    my $labels = sprintf $chart_labels, $xaxis1, $xaxis2, $range, $range;
    $titles =~ s/ /+/g;
    $labels =~ s/ /+/g;
    return join('&', $chart_api, $titles, $labels, $colour, $chart_filler, $datum);
}

sub _set_max {
    my $max = shift;
    my ($limit,$max_limit) = (10,10000000);

    return $limit   if($max <= $limit);
    while($limit < $max_limit) {
        if($max > $limit) {
            $limit *= 10;
            next;
        }

        my $inc10 = int($limit / 10);
        my $inc50 = int($limit / 20);
        for(my $inc = $inc10 ; $inc < $limit ; $inc += $inc50) {
            #print STDERR "\n# max=$max, limit=$limit, inc=$inc\n";
            return $inc if($max <= $inc);
        }

        return $limit;
    }

    return $max_limit;
}

sub _set_range {
    my ($min,$max) = @_;
    my $step = 1;

       if($max <=  10)      { $step = 1        }
    elsif($max <=  100)     { $step = 10       }
    elsif($max <=  500)     { $step = 50       }
    elsif($max <=  1000)    { $step = 100      }
    elsif($max <=  10000)   { $step = 1000     }
    elsif($max <=  100000)  { $step = 10000    }
    elsif($max <=  1000000) { $step = 100000   }
    else                    { $step = 1000000  }

    my @r;
    for(my $r = $min; $r < ($max+$step); $r += $step) {
        my $x = $r < 1000000 ? $r < 1000 ? $r : ($r/1000) . 'k' : ($r/1000000) . 'm';
        push @r, $x;
    };
    #print "range=".(join('|',@r))."\n";
    return join('|',@r);
}

sub _y_format {
    my $num = shift || return '';
    return ''   unless(defined $num);
    return $1.'k'   if($num =~ /^(\d{1,3})000$/);
    return $1.'m'   if($num =~ /^(\d{1,3})000000$/);
    return $num;
}

1;

__END__

=head1 DATABASE SCHEMA

    DROP TABLE IF EXISTS `monitor`;
    CREATE TABLE `monitor` (
      now           timestamp,
      day           int(2) not null default 0,
      month         int(2) not null default 0,
      year          int(4) not null default 0,
      name_count    int(10) not null default 0,
      page_count    int(10) not null default 0,
      page_weight   int(10) not null default 0,
      PRIMARY KEY  (now,day,month,year)
    );

=head1 SEE ALSO

  Labyrinth

=head1 AUTHOR

Barbie, <barbie@missbarbell.co.uk> for
Miss Barbell Productions, L<http://www.missbarbell.co.uk/>

=head1 COPYRIGHT & LICENSE

  Copyright (C) 2008-2012 Barbie for Miss Barbell Productions
  All Rights Reserved.

  This module is free software; you can redistribute it and/or
  modify it under the Artistic License 2.0.

=cut
