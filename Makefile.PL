use ExtUtils::MakeMaker;
WriteMakefile(
    NAME            => 'CPAN::Testers::WWW::Reports',
    'VERSION_FROM'  => 'lib/CPAN/Testers/WWW/Reports.pm',
    PREREQ_PM       => {
                'Clone'                             => '0',
                'CPAN::Testers::Common::Article'    => '0',
                'CPAN::Testers::Common::Utils'      => '0',
                'CPAN::Testers::Fact::LegacyReport' => '0',
                'CPAN::Testers::Fact::TestSummary'  => '0',
                'Cwd'                               => '0',
                'Email::Address'                    => '0',
                'File::Path'                        => '0',
                'File::Slurp'                       => '0',
                'GD::Graph::lines'                  => '0',
                'GD::Graph::colour'                 => '0',
                'HTML::Entities'                    => '0',
                'JSON::XS'                          => '0',
                'Labyrinth'                         => '5.04',
                'Labyrinth::Plugin::Core'           => '5.06',
                'Labyrinth::Plugin::Requests'       => '1.00',
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
                'Getopt::Long'                      => '0',
    },

    NO_META         => 1,

    ($] >= 5.005 ?    ## Add these new keywords supported since 5.005
      (ABSTRACT     => 'The CPAN Testers Reports website',
       AUTHOR       => 'Barbie <barbie@cpan.org>') : ()),
);
