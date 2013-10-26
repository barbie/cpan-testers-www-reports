#!/usr/bin/perl

use strict;
use warnings;
use 5.006;

use ExtUtils::MakeMaker;

WriteMakefile(
    AUTHOR              => 'Barbie <barbie@cpan.org>',
    NAME                => 'CPAN::Testers::WWW::Reports',
    VERSION_FROM        => 'lib/CPAN/Testers/WWW/Reports.pm',
    ABSTRACT            => 'The CPAN Testers Reports website',
    NO_META             => 1,
    PREREQ_PM           => {

        # prereqs
        'Class::Accessor::Fast'             => '0',
        'Clone'                             => '0',
        'CPAN::Testers::Common::Article'    => '0',
        'CPAN::Testers::Common::Utils'      => '0',
        'CPAN::Testers::Fact::LegacyReport' => '0',
        'CPAN::Testers::Fact::TestSummary'  => '0',
        'Cwd'                               => '0',
        'Data::Dumper'                      => '0',
        'Data::FlexSerializer'              => '0',
        'Email::Address'                    => '0',
        'File::Path'                        => '0',
        'File::Slurp'                       => '0',
        'GD::Graph::lines'                  => '0',
        'GD::Graph::colour'                 => '0',
        'HTML::Entities'                    => '0',
        'JSON::XS'                          => '0',
        'Labyrinth::Audit'                  => '5.13',
        'Labyrinth::DBUtils'                => '5.13',
        'Labyrinth::DTUtils'                => '5.13',
        'Labyrinth::MLUtils'                => '5.13',
        'Labyrinth::Mailer'                 => '5.13',
        'Labyrinth::Plugin::Articles::Site' => '5.10',
        'Labyrinth::Plugin::Base'           => '5.13',
        'Labyrinth::Plugin::Requests'       => '1.00',
        'Labyrinth::Session'                => '5.13',
        'Labyrinth::Support'                => '5.13',
        'Labyrinth::Users'                  => '5.13',
        'Labyrinth::Variables'              => '5.13',
        'Labyrinth::Writer'                 => '5.13',
        'Metabase::Resource'                => '0',
        'Sort::Versions'                    => '0',
        'Time::Local'                       => '0',
        'version'                           => '0',
        'WWW::Mechanize'                    => '0',
        'XML::RSS'                          => '0',
        'YAML::XS'                          => '0',

        # for testing only
        'IO::File'                          => '0',
        'Test::More'                        => '0',

        # for toolkit scripts
        'File::Find::Rule'                  => '0',
        'Getopt::Long'                      => '0'

    }
);
