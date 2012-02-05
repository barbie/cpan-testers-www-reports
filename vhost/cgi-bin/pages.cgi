#!/usr/bin/perl -w
use strict;

use vars qw($VERSION);
$VERSION = '3.34';

#----------------------------------------------------------
# Additional Modules

use lib qw|. ./lib ./plugins|;

#use CGI::Carp			qw(fatalsToBrowser);

use Labyrinth;

#----------------------------------------------------------

my $lubi = Labyrinth->new();
$lubi->run('/var/www/reports/cgi-bin/config/settings.ini');

1;

__END__
