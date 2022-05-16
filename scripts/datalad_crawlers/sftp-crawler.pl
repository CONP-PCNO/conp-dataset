
#!/usr/bin/perl
#
#  sftp_crawler.pl - crawl a dataset on sftp-conp.acelab.ca
#                    - EOB - Mar 03 2020
#
# usage: sftp_crawler.pl $username $password  $local_directory $remote_directory $inlist
#
# $local_directory  == working directory on local computer
# $remote_directory == directory on sftp.conp.ca **relative to home directory of data provider**
# $inlist           == local file containing list of files to download
#
########################################

use lib '/perl5/x86_64-linux-gnu-thread-multi';   # these may need adjusting for location of, or installation in, local perl directory

my $username          = $ARGV[0];
my $password          = $ARGV[1];
my $local_directory   = $ARGV[2];
my $remote_directory  = $ARGV[3];
my $inlist            = $ARGV[4];

my $remote_host       = "sftp.conp.ca";

my $inline       = "";
my $remote_file  = "";
my $local_file   = "";
my $line_count   = 0;

open(IN_LARGE, "$inlist") || die "Can't open $inlist to read";

while ($inline = <IN_LARGE>) {
    ++$line_count;
    print "Reading line ".$line_count. " of ".$inlist."\n";
    chomp $inline;
    $remote_file = $inline;
    $local_file  = $remote_file;
    $remote_file =~ s#data/proftpd/##;
    $local_file  =~ s/$remote_directory/$local_directory/;
    $local_file  =~ s#/data/proftpd/users/##;
    $remote_file = "https://".$remote_host.$remote_file;
#    print "Remote file = ".$remote_file."\n";
#    print "Local file  = ".$local_file."\n";

    unless (-e $local_file) {  # do not regenerate files that already exist (for case of interrupted crawl)
        system "git annex addurl $remote_file --file $local_file";
    }
    else {
        print "$local_file already exists\n";
    }
}
close IN_LARGE;

exit();
