package CPAN::Testers::WWW::Reports;

use warnings;
use strict;

our $VERSION = '3.39';

1;

__END__

=head1 NAME

CPAN::Testers::WWW::Reports - The CPAN Testers Reports website.

=head1 DESCRIPTION

This distribution contains all the code used to run the CPAN Testers Reports 
website.

=head1 VHOST FILES

The CPAN Testers Reports website is built on top of the Labyrinth Website 
Management System. As such, much of the code used to drive the website is
contained within the Labyrinth and associated plugin prerequisites. In order
to define the website in terms of functionality, layout and style, the files 
within the './vhost' directory of this distribution should be installed into 
your web server's virtual host directory.

Included in the distribution is a C<vhost.conf> file, which contains the 
virtual host settings to implement the site using the Apache Web Server.

=head1 ADDITIONAL COPYRIGHT

This distribution includes TinyMCE [1], a Javascript WYSIWYG Editor used within
the site. TinyMCE is distributed under the GNU Lesser General Public License 
Version 2.1, and all files within the './vhost/html/js/tiny_mce' directory
are copyright of the TinyMCE project.

[1] http://tinymce.moxiecode.com/

=head1 SEE ALSO

L<Labyrinth>, 

L<http://www.cpantesters.org>

=head1 AUTHOR

Barbie, <barbie@missbarbell.co.uk> for
Miss Barbell Productions, L<http://www.missbarbell.co.uk/>

=head1 COPYRIGHT & LICENSE

  Copyright (C) 2008-2012 Barbie for Miss Barbell Productions
  All Rights Reserved.

  This module is free software; you can redistribute it and/or
  modify it under the Artistic License 2.0.

=cut
