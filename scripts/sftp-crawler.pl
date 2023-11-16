#!/usr/bin/perl
#
#  sftp_crawler.pl - crawl a dataset on sftp-conp.acelab.ca
#                    - EOB - Mar 03 2020 - reworked Apr 21 2022
#
# usage: sftp_crawler.pl $local_projectname $username $password $local_directory $remote_directory $inlist
#
#    see https://github.com/CONP-PCNO/conp-documentation/blob/master/Developers-Notes/CONP_VM_setups_and_maintenance/SFTP_community_server/CONP_data_upload_admin.md for details
#
#
########################################

# use lib '/home/eaobrien/perl5/lib/perl5/x86_64-linux-gnu-thread-multi';
use Net::SFTP::Foreign;
use Net::SFTP::Foreign::Attributes;
use Net::SFTP::Foreign::Constants qw(:error :status);

my $username          = $ARGV[0];
my $password          = $ARGV[1];
my $local_directory   = $ARGV[2];
my $remote_directory  = $ARGV[3];
my $inlist            = $ARGV[4];

my $remote_host      = "sftp.conp.ca";

my $sftp_connection = Net::SFTP::Foreign->new($remote_host,user=>$username,password=>$password, port=>"7500");

my $inline       = "";
my $remote_file  = "";
my $local_file   = "";
my $line_count   = 0;

open(IN_LARGE, "$inlist") || die "Can't open $inlist to read";

while ($inline = <IN_LARGE>) {
    chomp $inline;
    $remote_file = $inline;
	$local_file  = $remote_file;
    $remote_file =~ s/data\/proftpd\///;
	$local_file  =~ s/$remote_directory/$local_directory/;
    $local_file =~ s/\/data\/proftpd\/users\/$username//;

	$remote_file = "https://".$remote_host.$remote_file;
#	print "linking $remote_file as $local_file\n";
	unless (-e $local_file) {  # do not regenerate files that already exist (for case of interrupted crawl)
    	system "git annex addurl $remote_file --file $local_file";
	}
	else {
		print "$local_file already exists\n";
	}
	print "processed line $line_count\n";
	++$line_count;
}
close IN_LARGE;

exit();
