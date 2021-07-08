#!/usr/bin/perl -w
use File::Find;

sub main {
   
    my $users_dir = "dataset-medium";
    my $user_to_show = 'z3275760';

    my @file_list;
    find ( sub {
    return unless -f;       #Must be a file
    return unless /^comment\.txt$/;  #Must match with `comment.txt`
    push @file_list, $File::Find::name;
    }, $users_dir ); # from http://stackoverflow.com/a/17756047
    
    for my $file (@file_list) {
        open my $p, $file or die "Cannot open $file: $!";
        my $comment = join '', <$p>;
        close $p;
        $comment =~ /from=(.*)/;
        if ($1 eq $user_to_show) {
            $file =~ /^(.*)\/posts\/([0-9]+)/;
            open my $f, "$1/posts/$2/post.txt" or die "Can not open $1//posts/$2/post.txt: $!";
            my $original_post = join '', <$f>;
            close $f;
            $original_post =~ /message=(.*)/;
            print "$1\n";
            $original_post =~ /from=(.*)/;
            print "from $1\n";
            $comment =~ /message=(.*)/;
            print "\t$1\n";
        }
    }
}

main ();