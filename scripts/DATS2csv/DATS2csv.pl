#!/usr/bin/perl
#
#  DATS2csv.pl - crawl all DATS.json files from CONP and output a single .csv file
#                    - EOB - Mar 16 2023
#
# usage: DATS2csv.pl t
#
#  Generate the input file list by downloading conp-dataset using DataLad and then extracting
#  the locations of all the DATS.json files in the directory
# 
#  find /data/temp-datasets/emmetaobrien/conp-dataset -type f | grep DATS.json > t
# 
# Right now (Mar 2023) the contents of conp_dataset are a little over 10,000 files so this may take some time
#
########################################

# use lib '/home/eaobrien/perl5/lib/perl5/x86_64-linux-gnu-thread-multi';

my @all_entities;                     # array of arrays to store input data
my $inlist       = @ARGV[0];
my $inline       = "";
my $listline	 = "";
my $maskfile     = "fieldlist.txt";
my $maskline     = "";
my $outfile      = "DATS.json-summary.csv";
my $json_string  = "";
my $infilecount  = 0;
my $sigchar      = "";
my $max_col      = 0;

open(IN_LIST, "$inlist") || die "Can't open $inlist to read";


while ($listline = <IN_LIST>) {
    chomp $listline;
#	print "Reading file $listline\n";

    # read file

    my $key           = "";
    my $key_component = "";
    my $korv_state    = "";
    my $value         = "";
    my $value_length  = 0;
	my $kc_length     = 0;
    my $key_depth     = 0;
    my $stack_depth   = 0;
	my $debug_length  = 0;
    my $entity_count  = 0;
    my @context_stack = ();
    my @array_pos     = ();
	my $last_char     = "";
    my $outkey        = "";
    my $col_count     = 0;

    open (IN, $listline);
    local $/; # slurp mode
    $json_string = <IN>;
    $json_string =~ s/\n//g;
	$json_string =~ s/\t//g;
	$json_string =~ s/\\\"/'/g;
#    print "$json_string\n";
     until ($json_string eq "") {
		if (substr($json_string,0,1) =~ /([\{|\}|\"|\:|\[|\]|\,|\d])/) {  # a meaningful formatting character
        	$sigchar = substr($json_string,0,1);
        }
		else {
			$json_string =~ s/^\s+//;            		
			next;
		}
#		$debug_length = length($json_string);
#        print "$sigchar $debug_length\n";
        $json_string = substr($json_string,1);
 #       print "$json_string\n";
		if ($sigchar eq "{")  {  # opening a layer of nesting
			$context_stack[$stack_depth] = "{";
			++$stack_depth;
			++$key_depth;
			$korv_state  = "key";
			$json_string =~ s/^\s+//;  # left trim spaces
		}
        if ($sigchar eq "}") {
			$context_stack[$stack_depth] = "";
			--$stack_depth;
			$korv_state = "key";
			$key =~ /(^.*)\./;  # greedy match should pick up everything before the last .
			$key = $1;
			--$key_depth;			 				
			if ($context_stack[$stack_depth] eq "[") {
				$key =~ /(^.*)\./;  # greedy match should pick up everything before the last .
				$key = $1;
				++$array_pos[$stack_depth];
				if ($array_pos[$stack_depth] < 10) {
					$key .= ".0".$array_pos[$stack_depth];   # pad for better sorting/readability
				}				
				else {				
					$key .= ".".$array_pos[$stack_depth];				
				}
			}
         }
		 if ($sigchar eq "[") {
			$context_stack[$stack_depth] = "[";
			$array_pos[$stack_depth]     = 1;
			$key .= ".0".$array_pos[$stack_depth];
			++$key_depth;			 
            ++$stack_depth;
			$json_string =~ s/^\s+//;          
         }
         if ($sigchar eq "]") {
			$context_stack[$stack_depth] = "";
            $array_pos[$stack_depth]     = 0;
			--$stack_depth;
			$key =~ /(^.*)\./;  # greedy match should pick up everything before the last .
			$key = $1;
			--$key_depth;
		}
		if ($sigchar eq ",") {
			--$key_depth;
			$key =~ /(^.*)\./;  # greedy match should pick up everything before the last .
			$key = $1;
			if ($context_stack[$stack_depth-1] eq "[") {
				++$array_pos[$stack_depth-1];
				if ($array_pos[$stack_depth-1] < 10) {
					$key .= ".0".$array_pos[$stack_depth-1];
				}				
				else {				
					$key .= ".".$array_pos[$stack_depth-1];				
				}			
			}
			$korv_state = "key";
		}
		if ($sigchar eq ":") {
			$korv_state = "value";
		}
		if ($sigchar eq "\"") {
			if ($key =~ /formats\.\d\d/) { # exception for entity with non-standard format, which is my own fault
				$korv_state = "value";   # no keys, just values
			}
			if ($korv_state eq "key") {
				$json_string =~ /(.*?\")(.*)$/;
				$key_component = $1; $json_string = $2;
				$kc_length = length($key_component) - 1; # cut terminal "
                $key_component = substr($key_component,0, $kc_length);
				if (($key_depth > 0) && (substr($key,-1) ne ".")) {
					$key .= ".";
				}
				$key .= $key_component;
				++$key_depth;				
			}            
			if ($korv_state eq "value") {
				$json_string =~ /(^.*?\")(.*)$/;
				$value = $1; $json_string = $2;
				$value_length = length($value) - 1; # cut terminal "
                $value = substr($value,0, $value_length);
				if ($value eq "") {  # do not store empty values
					$json_string =~ s/^\s+//;
           			next;
				}
 				else {
					$outkey = substr($key,1);  # cut the initial . representing the root level
											   # this is for neat output rather than function
					$all_entities[$infilecount][$col_count][0] = $outkey;
					$all_entities[$infilecount][$col_count][1] = $value;
					++$col_count;
#					print "Writing out $col_count $outkey => $value\n\n";
				}  
			}
		}
		if ($sigchar =~ /\d/) {   # trapping a numerical value
			if ($korv_state eq "value") {
				$json_string = $sigchar.$json_string;
				$json_string =~ /^(\d+(?:\.\d+)?|\.\d+)(.*)$/;  # match any digits or decimal point until next 
				$value = $1; $json_string = $2; # first digit is the character we are testing 
				$outkey = substr($key,1);       # cut the initial . representing the root level
											    # this is for neat output rather than function
				$all_entities[$infilecount][$col_count][0] = $outkey;
				$all_entities[$infilecount][$col_count][1] = $value;
				++$col_count;
#				print "Writing out $col_count $outkey => $value\n";
                $korv_state = "key";
			}
        }		
		$json_string =~ s/^\s+//;
#		print "context = $context_stack[$stack_depth-1] array position = $array_pos[$stack_depth-1]\n";
#		print "key == $key key depth = $key_depth value == $value state == $korv_state\n remaining string starts||". substr($json_string,0,30)."||\n\n";			
    }
    close IN;	

#	print "Reading row $infilecount total columns $col_count\n";

	# reformat the extraProperties entries
	
    my @temp_extra = ();
	my $c = $x = 0; 
	while ($c < $col_count) {
		if ($all_entities[$infilecount][$c][0] =~ /^extraProperties\.\d\d\.category/) {
			$temp_extra[$x][0] = "extraProperties.".$all_entities[$infilecount][$c][1];   #extract "category" and "value" values
			$temp_extra[$x][1] = $all_entities[$infilecount][$c+1][1];
			$all_entities[$infilecount][$c][0] = "dummy";                        #remove originals
			$all_entities[$infilecount][$c][1] = "dummy";
			$all_entities[$infilecount][$c+1][0] = "dummy";
			$all_entities[$infilecount][$c+1][1] = "dummy";
#			print "extraproperties category $temp_extra[$x][0] value $temp_extra[$x][1]\n";
			++$x;
		}
		++$c;
	}

	my $x2 = 0;
	while ($x2 < $x) {														# and add back to the end of the row
		$all_entities[$infilecount][$col_count][0] = $temp_extra[$x2][0];
		$all_entities[$infilecount][$col_count][1] = $temp_extra[$x2][1];
		++$col_count; ++$x2;
	}

	if ($infilecount == 0) {
		$max_col = $col_count;
	}
	else {
		if ($col_count > $max_col) {
			$max_col = $col_count;
		}
	}

    ++$infilecount;
    $col_count = 0;
    $sigchar = "";
}
close IN_LIST;

# extract unique column headers into single array

my @merged_keys  = ();
my @merged_vals  = ();
my %merge_ref;
my %handled;
my $all_row = 0;
my $all_col = 0;
my $merge_count = 0;
my $search_string = ""; 
while ($all_row < $infilecount) {
    if ($all_row == 0) {  # first row
		$all_col = 0;
		while ($all_col < $max_col) {
			$merged_keys[$merge_count]    = $all_entities[$all_row][$all_col][0];
			$merged_vals[$merge_count]    = $all_entities[$all_row][$all_col][1];
			$merge_ref{$merged_keys[$merge_count]} = $merge_count;
			$handled{$merged_keys[$merge_count]}   = 0;
			++$merge_count;
			++$all_col;
		}
	}
	else {
		while ($all_col < $max_col) {
			$search_string = $all_entities[$all_row][$all_col][0];
			unless (grep(/^$search_string$/,@merged_keys)) {   # only store it if it does not already exist
				$merged_keys[$merge_count]    = $all_entities[$all_row][$all_col][0];
				$merged_vals[$merge_count]    = $all_entities[$all_row][$all_col][1];
				$merge_ref{$merged_keys[$merge_count]} = $all_col;
				$handled{$merged_keys[$merge_count]}   = 0;
				++$merge_count;
			}
			++$all_col; 
		}
	}
#	print "Merged column set length $merge_count at row $all_row\n";
	++$all_row;
}


# read in the externally defined ordering (list of fields from CONP documentation)

my @templates  = ();
my $temp_count = 0;
open(MASK, $maskfile)  || die "cannot open $maskfile to read";
while ($maskline = <MASK>) {
	chomp $maskline ;
	$maskline =~ s/\s-\s/\\\.\\d\\d\\\./g; # building mask with correct \d characters for regex
#   print $maskline."\n";
	$templates[$temp_count] = $maskline;  # read this string as a regex pattern
	++$temp_count;
}

close MASK;

# search keys for each template in turn

my @output_header = ();
my @output_array  = ();
my $out_column    = 0;
my $out_row       = 0;

my $tc = $mc = 0;
my %subhash;
my $debug_count;
while($tc < $temp_count) {
    %subhash = ();
    my $search_string = qr/$templates[$tc]/;

	# extract subset of merged columns matching this template
	
#	print "Searching search string $tc $search_string\n"; 

	$mc = 0;
    $debug_count = 0;
	while ($mc < $merge_count) {
		if (($merged_keys[$mc] =~ /$search_string/) && ($handled{$merged_keys[$mc]} == 0)) {
			$subhash{$merged_keys[$mc]} = $merged_vals[$mc];
#			print "key $merged_keys[$mc] value $merged_vals[$mc]\n";
			$handled{$merged_keys[$mc]} = 1;
			++$debug_count;
		}
		++$mc;
	}

#	print "retrieved $debug_count columns matching search string\n";

	# look up each key in every row of @all_entities

	foreach $key (sort keys %subhash) { # should sort them in alphabetical order
		$output_header[$out_column] = $key;
		$out_row = 0;
		while ($out_row < $infilecount) {
			if (exists $all_entities[$out_row][$merge_ref{$key}][1]) {
				$output_array[$out_column][$out_row] = $all_entities[$out_row][$merge_ref{$key}][1];
#				print "at column $key at position $merge_ref{$key} we find $all_entities[$out_row][$merge_ref{$key}][1]\n";
			}
			else {
				$output_array[$out_column][$out_row] = "";
			}
			++$out_row;
		}
		++$out_column;   # unlike the other counters $out_column is _not_ reset to 0 within this logic
	}

	++$tc;	
}

# (trap exceptions here)


open TEST, ">temp_debug_file" || die "cannot open temp_debug_file";
$x = 0;
while ($x < $merge_count) {
	if ($handled{$merged_keys[$x]} == 0) {  # has not been handled 
		print TEST "$x $merged_keys[$x] $merged_vals[$x]\n";
	}
	++$x;
}
close TEST;


# output

my $header_line  = "";
my @value_line   = ();
$oc           = 0;
my $out_row      = 0;   # variable naming would be more consistent if "or" was not a reserved word

# first entries

$header_line = '"'.$output_header[$oc].'"';
while ($out_row < $infilecount) {
	$value_line[$out_row] = '"'.$output_array[$oc][$out_row].'"';
	++$out_row;
}
++$oc;

# now concatenate all the rest 

while ($oc < $out_column) {
	unless (($output_header[$oc] =~ /hasPart/) || ($output_header[$oc] =~ /^dummy$/)) {            # remove these lines for the moment
		$header_line .= ',"'.$output_header[$oc].'"';
		$out_row      = 0;
		while ($out_row < $infilecount) {
			$value_line[$out_row] .= ',"'.$output_array[$oc][$out_row].'"';
			++$out_row;
		}
	}
	++$oc;
}


open (OUT, ">$outfile");
print OUT $header_line."\n";
$out_row      = 0;
while ($out_row < $infilecount) {
	print OUT $value_line[$out_row]."\n";
	++$out_row;
}

close OUT;

exit();


