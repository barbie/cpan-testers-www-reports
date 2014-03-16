#!/usr/bin/perl -w
use strict;

use vars qw($VERSION);
$VERSION = '3.47';

#----------------------------------------------------------------------------

=head1 NAME

reports-summary.cgi - program to return graphical status of a CPAN distribution

=head1 SYNOPSIS

  perl reports-summary.cgi

=head1 DESCRIPTION

Called in a CGI context, returns the current reporting statistics for a CPAN
distribution, depending upon the POST parameters provided.

=cut

#----------------------------------------------------------
# Additional Modules

use lib qw|. ./lib ./plugins|;

#use CGI::Carp			qw(fatalsToBrowser);

use Labyrinth;

#----------------------------------------------------------

my $lab = Labyrinth->new();
$lab->run('/var/www/reports/cgi-bin/config/settings.ini');

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

  Copyright (C) 2008-2014 Barbie <barbie@cpan.org>

  This module is free software; you can redistribute it and/or
  modify it under the Artistic License 2.0.

=cut
