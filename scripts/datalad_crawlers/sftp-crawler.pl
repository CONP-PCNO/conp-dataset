
#!/usr/bin/perl
#
#  sftp_crawler.pl - crawl a dataset on sftp-conp.acelab.ca
#                    - EOB - Mar 03 2020
#
# usage: sftp_crawler.pl $local_projectname $username $password  $local_directory $remote_directory $inlist
#
# $local_directory  == working directory on local computer
# $remote_directory == directory on sftp.conp.ca **relative to home directory of data provider**
# $inlist           == local file containing list of files to download
#
########################################

use lib '/perl5/x86_64-linux-gnu-thread-multi';   # these may need adjusting for location of, or installation in, local perl directory
use Net::SFTP::Foreign;
use Net::SFTP::Foreign::Attributes;
use Net::SFTP::Foreign::Constants qw(:error :status);

my $local_projectname = $ARGV[0];
my $username          = $ARGV[1];
my $password          = $ARGV[2];

my $local_directory   = $ARGV[3];
my $remote_directory  = $ARGV[4];
my $remote_host       = "sftp.conp.ca";

my $sftp_connection = Net::SFTP::Foreign->new($remote_host,user=>$username,password=>$password, port=>"7500");

my $inlist       = "/home/eaobrien/perlscripts/index";
my $inline       = "";
my $remote_file  = "";
my $local_file   = "";

# code for copying small files and saving directly into github; has not currently in use
# TODO; decide on consistent conditions/policy for what goes in this set and what in the set of large files for link generation

#open(IN_SMALL, "$inlist_small") || die "Can't open $inlist_small to read";

#while ($inline = <IN_SMALL>) {
#    chomp $inline;
#   $remote_file = $inline;
#    $remote_file =~ s/\/data\/proftpd\/users\/$username//;
#   $local_file  = $local_directory.$remote_file;
#   $local_file  =~ s/\/mics//;

#    print "Remote file = $remote_file\nLocal file = $local_file\n";

#   if ($sftp_connection->get("$remote_file","$local_file")) {
#       print "$remote_file downloaded successfully\n";
#       system "git add $local_file";
#   }
#   else {
#       print $sftp_connection->error."\n";
#       exit();
#   }
#}

open(IN_LARGE, "$inlist") || die "Can't open $inlist to read";

while ($inline = <IN_LARGE>) {
    chomp $inline;
    $remote_file = $inline;
    $local_file  = $remote_file;
    $remote_file =~ s/data\/proftpd\///;
    $local_file  =~ s/$remote_directory/$local_directory/;
    $local_file  =~ s/\/data\/proftpd\/users\/$username//;

    $remote_file = "https://".$remote_host.$remote_file;
    
    unless (-e $local_file) {  # do not regenerate files that already exist (for case of interrupted crawl)
        system "git annex addurl $remote_file --file $local_file";
    }
    else {
        print "$local_file already exists\n";
    }
}
close IN_LARGE;

exit();
