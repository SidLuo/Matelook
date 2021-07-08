#!/usr/bin/perl -w

# written by andrewt@cse.unsw.edu.au September 2016
# as a starting point for COMP2041/9041 assignment 2
# http://cgi.cse.unsw.edu.au/~cs2041/assignments/matelook/

use CGI qw/:all/;
use CGI::Carp qw/fatalsToBrowser warningsToBrowser/;
use CGI::Cookie;
use POSIX qw(strftime);
use DateTime;
use DateTime::Format::ISO8601;
use File::Find;

sub main() {
    %cookies = CGI::Cookie->fetch;
   
    # define some global variables
    $debug = 1;
    $users_dir = "dataset-medium";
    $default_profile_img = "https://d2wnxi2v4fzw0h.cloudfront.net/assets/fallback/preview_default_profile.png";
    
    if ($cookies{'ID'}) {
         # fetch the current user;
	    $user = $cookies{'ID'}->value;
        user_page(); #decides which page to show
    } else {
        # redirect to login page
        login();
    }
}


# login page
sub login() {
    my $username = param('username') || '';
    my $password = param('password') || '';
    my $login_failed = 0;
    if ($username && $password) {
        if ($username =~ /^z[0-9]{7}$/) {
            if (-e glob("$users_dir/$username") and -d glob("$users_dir/$username")) {
                open my $p, "$users_dir/$username/user.txt" 
                or die "Can not open $users_dir/$username/user.txt: $!";
                my $everything = join '', <$p>;
                close $p;
                $everything =~ /password=(.*)/;
                my $auth = $1;
                if ($password eq $auth) {
                    login_success ($username);
                    return;
                }
            }
        }
        $login_failed = 1;
    }
    print   login_page_header(),
            h2('Matelook'), "\n<p>\n";
    print login_failure() if ($login_failed);
    print   start_form(-class=>"register-form"), "\n",
            textfield(-name=>'email', -type=>"text", -placeholder=>"email address"), "\n",
            textfield(-name=>'username', -type=>"text", -placeholder=>"zid"), "\n",
            '<input name="password" type="password" placeholder="password"/>', "\n",
            "<p class=\"message\">Already registered? <a href=\"#\">Sign In</a></p>", "\n",
            submit(-value => 'Create Account', -name => "create", -class=> 'mybutton'), "\n",
            end_form,"\n",
            
            start_form(-class=>"login-form"), "\n",
            textfield(-name=>'username', -type=>"text", -placeholder=>"username"), "\n",
            '<input name="password" type="password" placeholder="password"/>', "\n",
            submit(-value => 'Login', -name => 'Login', -class=> 'mybutton'), "\n",
            end_form, "\n",
            "<p class=\"message\">Not registered? <a href=#>Create an account</a></p>", "\n",
            "</div>\n</div>\n",
            page_trailer();

}

# redirect to profile page
sub login_success {
    my ($username) = @_;
    my $cookie1 = CGI::Cookie->new(-name    =>  'ID',
                                   -value   =>  "$username",
                                   -expires =>  '+10d',
                                   );
    print header(-cookie=>$cookie1),
          start_html(-title=>'Redirecting...',
                    -style => "matelook.css",
                    -head=>meta({-http_equiv => 'Refresh',
                            -content=> '3; matelook.cgi'}), -BGCOLOR=>'#fbf6d9'
                    ); 
    #from http://www.perlmonks.org/bare/?displaytype=displaycode;node_id=325455
    warningsToBrowser(1);
	print "Welcome, ".get_name($username)."\n";
    print end_html;
}

#
# Decide which page to show
#
sub user_page {
    my $search = param('search') || '';
    my $view_profile = param('view_profile') || '';
    my $view_post = param('view_post') || '';
    #my $view_mates = param('view_mates') || $user;
    
    if (defined param("logout")) {
        log_out();
        return;
    } elsif (defined param("search")) {
        print page_header();
        search($search);
    } elsif (defined param("edit") || defined param("submit")) {
        print page_header();
        edit_profile();
    } elsif (defined param("view_post")) {
        print page_header();
        view_post($view_post);
    } elsif (defined param("profile")) {
        print page_header();
        print_user($user);
    } elsif (defined param("view_profile")) {
        print page_header();
        print_user($view_profile);
    } else {
        print page_header();
        print_dash();
    }
    print page_trailer();
}

#
# from http://www.bloggermint.com/2011/06/css3-search-box-inspired-by-apple-com/
#
sub print_search {
    return <<eof
<form method="post" action="?" id="search" enctype="multipart/form-data">
<input name="search" type="text" size="40" placeholder="Search for Names" />
</form>
eof
}

#
# Show user dashboard
#
sub print_dash {

    open my $p, "$users_dir/$user/user.txt" or die "Can not open $users_dir/$user/user.txt: $!";
    my $info = join '', <$p>;
    close $p;
    #if (-e glob("$users_dir/$user/profile.jpg")) {
    #    print "<img src=\"$users_dir/$user/profile.jpg\" alt=\"$user Profile\" style=\"width:210px;height:210px;\">", "\n";
    #} else {
    #    my $profile_url = $default_profile_img;
    #    print "<img src=$profile_url alt=\"$user Profile\" style=\"width:210px;height:210px;\">", "\n";
    #}
    

    print "<aside id=\"sidebar\">", "\n";
    
    $info =~ /full_name=(.*)/;
    my $full_name = $1;
    print h2($full_name), "\n<p>\n";
    print "$user";
    
    print print_search();
    
    print start_form, "\n",
          submit({-class => "mybutton",-name => 'profile', value => 'View Profile'}), "\n",
          end_form, "\n",
          start_form, "\n",
          submit({-class => "mybutton",-name => 'logout', value => 'Log out'}), "\n",
          end_form, "\n",
          "</aside>", "\n",
          "<div class=\"post\">\n";
          
    make_post();
    my $delete = param('delete') || '';
    if (defined param("delete")) {
        print h2(delete_post($delete));
    } 
    print "</div>", p;
    
    $info =~ /mates=\[(.*)\]/;
    my $mates = $1;
    
    print_posts($mates.", ".$user);
    
}

sub make_post {
    my $i = 0;
    for ($i = 0; -e("$users_dir/$user/posts/$i/post.txt"); $i++) {}
    if (param('Save') && defined param('contents')) {
        my $contents = param('contents');
        $contents =~ s/\n/\\n/g;
        mkdir "$users_dir/$user/posts", 0755 if (not -e "$users_dir/$user/posts");
        mkdir "$users_dir/$user/posts/$i", 0755;
        open my $f, ">$users_dir/$user/posts/$i/post.txt" or die "Can not open $users_dir/$user/posts/$i/post.txt: $!";
        my $datestring = 'time='.DateTime->now()->iso8601().'+0000';
        print $f "message=$contents\n",
                 "from=$user\n",
                 "$datestring\n";
        close $f;
        print h2('Your post is published.');
        param('contents', "");
    } elsif (param('pictures') && defined param('contents')) {
        my $contents = param('contents');
        mkdir "$users_dir/$user/posts", 0755 if (not -e "$users_dir/$user/posts");
        mkdir "$users_dir/$user/posts/$i", 0755;
        open my $f, ">$users_dir/$user/posts/$i/post.txt" or die "Can not open $users_dir/$user/posts/$i/post.txt: $!";
        my $datestring = 'time='.DateTime->now()->iso8601().'+0000';
        $contents = "<img src=".$contents." alt=\"$datestring\">";
        print $f "picture=$contents\n",
                 "from=$user\n",
                 "$datestring\n";
        close $f;
        print h2("Your post is published.");
        param('contents', "");
    }
    print start_form,
        textarea(-name=>'contents', -rows=>10,-cols=>60, -placeholder=>"What's on your mind?"),
        p, submit({-class => "mybutton",-name => 'Save', value => 'Post'}),
        p, submit({-class => "mybutton",-name => 'pictures', value => 'Post picture as links'}),
        end_form;
}

sub print_posts {
    my ($users_to_show) = @_;
    my %time_diff;
    my @users_to_show = split /, /, $users_to_show;
    for my $user_to_show (@users_to_show) {
    
        # finding posts
        
        my $full_name = get_name($user_to_show);
        for my $file (glob "$users_dir/$user_to_show/posts/*/post.txt") {
            $file =~ /$users_dir\/$user_to_show\/posts\/(.*)\/post.txt/;
            my $i = $1;
            open my $f, $file or die "Can not open $file: $!";
            my $post = join '', <$f>;
            close $f;
            $post =~ /time=(.*)\+0000/;
            my $diff = calculate_time_diff($1);
            $time_diff{"$diff"}{'name'} = $full_name;
            $time_diff{"$diff"}{'num'} = $i;
            $time_diff{$diff}{'zid'} = $user_to_show;
            if ($post =~ /message=(.*)/) {
                $time_diff{"$diff"}{'content'} = $1;
            } elsif ($post =~ /picture=(.*)/) {
                $time_diff{"$diff"}{'picture'} = 'true';
                $time_diff{"$diff"}{'content'} = $1;
            }
        }
        
        # finding comments
        my @file_list;
        find ( sub {
        return unless -f;       #Must be a file
        return unless /^comment\.txt$/;  #Must match with `comment.txt`
        push @file_list, $File::Find::name;
        }, $users_dir ); # from http://stackoverflow.com/a/17756047
        
        for my $file (@file_list) {
            open my $p, $file or die "Can not open $file: $!";
            my $comment = join '', <$p>;
            close $p;
            $comment =~ /from=(.*)/;
            if ($1 eq $user_to_show) {
                $comment =~ /time=(.*)\+0000/;
                $diff = calculate_time_diff($1);
                
                $time_diff{"$diff"}{'name'} = $full_name;
                
                $comment =~ /message=(.*)/;
                $time_diff{$diff}{'content'} = $1;
                
                # add original post's infos
                $file =~ /^(.*)\/posts\/([0-9]+)\/comments\/([0-9]+)/;
                $time_diff{"$diff"}{'comment num'} = $3;
                open my $f, "$1/posts/$2/post.txt" or die "Can not open $1/posts/$2/post.txt: $!";
                my $original_post = join '', <$f>;
                close $f;
                $time_diff{"$diff"}{'num'} = $2;
                
                $original_post =~ /from=(.*)/;
                $time_diff{$diff}{'from'} = get_name($1);
                $time_diff{$diff}{'from_zid'} = $1;
                $time_diff{$diff}{'zid'} = $user_to_show;
                if ($original_post =~ /message=(.*)/) {
                    $time_diff{"$diff"}{'original post'} = $1;
                } elsif ($original_post =~ /picture=(.*)/) {
                    $time_diff{"$diff"}{'original picture'} = 'true';
                    $time_diff{"$diff"}{'original post'} = $1;
                }
                
                $original_post =~ /time=(.*)\+0000/;
                
                $time_diff{$diff}{'original post time'} = calculate_time_diff($1);
            }
        }
        
    }
    
    #sorting posts
    for my $key (sort {$a <=> $b} keys %time_diff) {
        my $content = $time_diff{$key}{'content'};
        $content = edit_content($content) if (not $time_diff{$key}{'picture'});
        my $time_tag = time_tag($key);
        
    
        print "<div class=\"post\">\n",
            "<div class=\"post_info\">\n",
            start_form({style=>"margin: 0; padding: 0", action=>"?"}),"\n",
            hidden({name=>"view_profile", value=>"$time_diff{$key}{'zid'}"}, style=>"display: inline;" ),"\n",
            submit({-name=>"view_profile", -class => 'timestamp_button', -value=>"$time_diff{$key}{'name'}"}),p,"\n",
            end_form, "\n",
            "<div class=\"timestamp\">\n";
            
        my $post_id;
        if ($time_diff{$key}{'from'}) {
            $post_id = $time_diff{$key}{'from_zid'};
        } else {
            $post_id = $time_diff{$key}{'zid'};
        }
        $post_id .= ",".$time_diff{$key}{'num'};
        $post_id .= ",".$time_diff{$key}{'comment num'} if ($time_diff{$key}{'from'});
        print start_form({style=>"margin: 0; padding: 0", action=>"?"}),"\n",
            hidden({name=>"view_post", value=>"$post_id", style=>"display: inline;"} ),"\n",
            submit({-name=>"view_post", -class => 'timestamp_button', -value=>"$time_tag"}), p, "\n",
            end_form, "\n",
            "</div>","\n";
            
        if ($time_diff{$key}{'zid'} eq $user) {
            print start_form({style=>"margin: 0; padding: 0", action=>"?"}),"\n",
                hidden({name=>"delete", value=>"$post_id", style=>"display: inline;"} ),"\n",
                submit({-name=>"delete", -class => 'timestamp_button', -value=>"Delete this post"}), p, "\n",
                end_form, "\n",
        }
        
        print "</div>", "\n",
            "<div class=\"caption\">\n", $content, "\n",
            start_form({style=>"margin: 0; padding: 0", action=>"?"});
        
        if ($time_diff{$key}{'from'}) {
            my $original = $time_diff{$key}{'original post'};
            $original = edit_content($original) if (not $time_diff{$key}{'original picture'});
            my $original_time_tag = time_tag($time_diff{$key}{'original post time'});
        
            print '<BLOCKQUOTE>', $original, '</BLOCKQUOTE>', p, "\n",
                hidden({name=>"view_profile", value=>"$time_diff{$key}{'from_zid'}"}, style=>"display: inline;" ),"\n",
                '<BLOCKQUOTE>', "Originally posted by ","\n",
                submit({-name=>"view_profile", class=>'profile_link', value=>"$time_diff{$key}{'from'}"}),"\n",
                $original_time_tag, p, '<BR>', '</BLOCKQUOTE>', p, "\n";
        }
        print end_form, "</div>", "</div>", p, "\n";
    }
}

#
# print single post with comments and other options (including delete, comment)
#
sub view_post {
    my ($post_id) = @_;
    $post_id =~ /^(z[0-9]{7}),([0-9]*)/;
    my $full_name = get_name($1);
    my $zid = $1;
    my $num = $2;
    
    open my $p, "$users_dir/$zid/posts/$num/post.txt" or die "Can not open $users_dir/$zid/posts/$num/post.txt: $!";
    my $post = join '', <$p>;
    close $p;
    my $content;
    if ($post =~ /message=(.*)/) {
        $content = edit_content($1);
    } else {
        $post =~ /picture=(.*)/;
        $content = $1;
    }
    $post =~ /time=(.*)\+0000/;
    my $time_tag = time_tag(calculate_time_diff($1));
    my $i = 0;
    for my $file (glob "$users_dir/$zid/posts/$num/comments/*/comment.txt") {$i++;}
    print "<div class=\"post\">\n",
            "<div class=\"post_info\">\n",
            start_form({style=>"margin: 0; padding: 0", action=>"?"}),"\n",
            hidden({name=>"view_profile", value=>"$zid", style=>"display: inline;"} ),"\n",
            submit({-name=>"view_profile", -class => 'timestamp_button', -value=>"$full_name"}),p,"\n",
            "<div class=\"timestamp\">\n",
            $time_tag, p, "\n",
            $i, " notes",  p, "\n",
            end_form, "\n",
            "</div>", "\n",
            "</div>", "\n",
            "<div class=\"post\">\n",
            "<div class=\"caption\">\n",
            start_form({style=>"margin: 0; padding: 0", action=>"?"}),
            $content, p, "\n",
            end_form, p, "\n",
            "</div></div>", "\n","<div class=\"post\">\n",
            h2(Comments), p, "\n";
    
    if (param('view_post') && defined param('comment')) {
        my $contents = param('comment');
        $contents =~ s/\n/\\n/g;
        mkdir "$users_dir/$user/posts/$num/comments", 0755 if (not -e "$users_dir/$user/posts/$num/comments");
        mkdir "$users_dir/$zid/posts/$num/comments/$i", 0755;
        open my $f, ">$users_dir/$zid/posts/$num/comments/$i/comment.txt" 
            or die "Can not open $users_dir/$zid/posts/$num/comments/$i/comment.txt: $!";
        my $datestring = 'time='.DateTime->now()->iso8601().'+0000';
        print $f "message=$contents\n",
                 "from=$user\n",
                 "$datestring\n";
        close $f;
        print h2('Your comment is posted.');
        param('contents', "");
    }
    print start_form,
        hidden({name=>"view_post", value=>"$post_id", style=>"display: inline;"} ),"\n",
        textarea(-name=>'comment', -rows=>10,-cols=>60, -placeholder=>"Post a comment"),
        p, submit({-class => "mybutton",-name => 'view_post', value => 'Post'}),
        end_form, '</div>';
    
    #sorting comments
    my %time_diff;
    for my $file (glob "$users_dir/$zid/posts/$num/comments/*/comment.txt") {
        my $i++;
        open my $p, $file or die "Can not open $file: $!";
        my $comments = join '', <$p>;
        close $p;
        
        $comments =~ /time=(.*)\+0000/;
        my $diff = calculate_time_diff($1);
        
        $comments =~ /from=(.*)/;
        $time_diff{"$diff"}{'name'} = get_name($1);
        $time_diff{$diff}{'zid'} = $1;
        
        $comments =~ /message=(.*)/;
        $time_diff{"$diff"}{'content'} = $1;
    }    
    for my $key (sort {$a <=> $b} keys %time_diff) {
        my $content = edit_content($time_diff{$key}{'content'});
        my $comment_time_tag = time_tag(calculate_time_diff($1));
        
        
        print "<div class=\"post\">\n","<div class=\"caption\">\n", p, 
            start_form({style=>"margin: 0; padding: 0", action=>"?"}),"\n",
            $content, p, "\n",
            hidden({name=>"view_profile", value=>$time_diff{$key}{'zid'}, style=>"display: inline;"} ),"\n",
            "Commented $comment_time_tag by ",
            submit({-name=>"view_profile", class=>'profile_link', value=>$time_diff{$key}{'name'} } ),"\n",
            end_form, '</div>', '</div>', "\n";
    }
}


sub delete_post {
    my ($post_id) = @_;
    my $full_name;
    my $zid;
    my $num;
    my $comment_num;
    if ($post_id =~ /^(z[0-9]{7}),([0-9]*)$/) {
        $full_name = get_name($1);
        $zid = $1;
        $num = $2;
    } elsif ($post_id =~ /^(z[0-9]{7}),([0-9]*),([0-9]*)$/) {
        $full_name = get_name($1);
        $zid = $1;
        $num = $2;
        $comment_num = $3;
    }
    my $deletedir;
    if ($zid eq $user) {
        $deletedir = "$users_dir/$user/posts/$num";
    } else {
        $deletedir = "$users_dir/$zid/posts/$num/comments/$comment_num";
    }
    return system("rm -rf $deletedir") ? "Unfortunately, deletion failed" : "Your post is deleted";
}

sub calculate_time_diff {
    my ($str) = @_;
    my $dt  = DateTime::Format::ISO8601->parse_datetime( $str );
    my $now = DateTime->now;
    my $diff = $now->epoch() - $dt->epoch();
    return $diff;
}

sub time_tag {
    my ($key) = @_;
    my $before;
    if ($key < 60) {$before = "Just now";}
    elsif ($key < 3600) {
        $before = int($key/60);
        if ($before > 1) {$before = "$before minutes ago";}
        else {$before = "$before minute ago";}
    } elsif ($key < 86400) {
        $before = int($key/3600);
        if ($before > 1) {$before = "$before hours ago";}
        else {$before = "$before hour ago";}
    } elsif ($key < 86400*30) {
        $before = int( $key/(86400) );
        if ($before > 1) {$before = "$before days ago";}
        else {$before = "$before day ago";}
    } elsif ($key < 86400*365) {
        $before = int( $key/(86400*30) );
        if ($before > 1) {$before = "$before months ago";}
        else {$before = "$before month ago";}
    } else {
        $before = int( $key/(86400*365) );
        if ($before > 1) {$before = "$before years ago";}
        else {$before = "$before year ago";}
    }
    return $before;
}

sub edit_content {
    my ($content) = @_;
    $content =~ s/&/&amp;/g;
    $content =~ s/</&lt;/g;
    $content =~ s/>/&gt;/g;
    $content =~ s/\\n/<p>/g;
    while ($content =~ /[^"](z[0-9]{7})/ or $content =~ /^(z[0-9]{7})/) {
        my $to_be_replaced = $1;
        my $str = "<input type=\"hidden\" name=\"view_profile\"  value=\"$1\" style=\"display: inline;\" />";
        my $name = get_name($1);
        $str .= "<input type=\"submit\" name=\"view_profile\" value=\"$name\" class=\"profile_link\">";
        $content =~ s/$to_be_replaced/$str/;
    }
    return $content;
}

sub get_name{
    my ($user_to_show) = @_;
    open my $p, "$users_dir/$user_to_show/user.txt" or die "Can not open $users_dir/$user_to_show/user.txt: $!";
    my $mate_info = join '', <$p>;
    close $p;
    $mate_info =~ /full_name=(.*)/;
    return $1;
}

sub print_user {
    my ($user_to_show)  = @_;
    print "<aside id=\"sidebar\">", "\n";
    print print_search();
    print start_form, "\n",
          submit({-class => "mybutton",-name => 'edit', value => 'Edit Profile', style=> 'block' }), "\n",
          submit({-class => "mybutton",-name => 'logout', value => 'Log out'}), "\n",
          end_form, "\n",
          "</aside>", "\n";
    my $user_filename = "$users_dir/$user_to_show/user.txt";
    open my $p, "$user_filename" or die "Can not open $user_filename: $!";
    
    my $info = join '', <$p>;
    close $p;
    
    if (-e glob("$users_dir/$user_to_show/profile.jpg")) {
        print "<img src=\"$users_dir/$user_to_show/profile.jpg\" alt=\"$user_to_show Profile\" style=\"width:210px;height:210px;\">", "\n";
    } else {
        my $profile_url = $default_profile_img;
        print "<img src=$profile_url alt=\"$user_to_show Profile\" style=\"width:210px;height:210px;\">", "\n";
    }
    
    my $full_name = get_name($user_to_show);
    my $home_suburb;
    if ($info =~ /home_suburb=(.*)/) {
        $home_suburb = $1;
    }
    $info =~ /birthday=(.*)/;
    my $birthday = $1;
    $info =~ /program=(.*)/;
    my $program = $1;
    print "<p><h2>$full_name</span></h2>\n<p>\n";
    print "$user_to_show";
    print "<div class=\"post\">\n",
        "<img src=\"https://cdn3.iconfinder.com/data/icons/stroke/53/Balloon-256.png\" alt=\"ballon icon\" style=\"width:15px;height:15px;\">",
        $birthday, p, "\n";
    if ($home_suburb) {
        print "<img src=\"https://www.materialui.co/materialIcons/maps/pin_drop_grey_192x192.png\" alt=\"location icon\" style=\"width:15px;height:15px;\">",
          $home_suburb, p, "\n";
    }
    print "<img src=\"http://p5cdn4static.sharpschool.com/UserFiles/Servers/Server_3171651/Image/citizen-manual-book-icon1.png\" alt=\"book icon\" style=\"width:15px;height:15px;\">",
        $program,"\n", p, "\n";
    
    $info =~ /home_latitude=(.*)/;
    my $lat = $1;
    $info =~ /home_longitude=(.*)/;
    my $long = $1;
    
    if ($lat && $long) {
        my $latlon = $lat.",".$long;
        # from http://www.w3schools.com/html/html5_geolocation.asp
        my $geo_url = "https://maps.googleapis.com/maps/api/staticmap?center=$latlon&zoom=14&size=400x300&sensor=false";

        print "<img src=$geo_url alt=\"home location map\">", "\n";
    }
    
    print "</div>",
        p;
    print "<div class=\"post\">\n";
    view_mates($user_to_show);
    print "</div>\n";
    
    print_posts($user_to_show);
}

sub edit_profile {
    if (defined param("submit")) {
        my $name = param('name');
        my $password = param('password') || '';
        my $new_password = param('new_password') || '';
        my $re_password = param('re_password') || '';
        my $email = param('email');
        my $dob = param('dob');
        my $program = param('program');
        my $home = param('home suburb');
        my $lat = param('home lat');
        my $long = param('home long');
        open my $p, "$users_dir/$user/user.txt" 
                or die "Can not open $users_dir/$user/user.txt: $!";
        my $everything = join '', <$p>;
        close $p;
        $everything =~ /password=(.*)/;
        my $auth = $1;
        $everything =~ /courses=\[(.*)\]/;
        my $courses = "courses=[$1]\n";
        $everything =~ /mates=\[(.*)\]/;
        my $mates = "mates=[$1]\n";
        if ($password eq $auth) {
            open my $f, ">$users_dir/$user/user.txt" 
                        or die "Can not open $users_dir/$user/user.txt: $!";
            my $write_in = "email=$email\n" if ($email);
            $write_in .= "full_name=$name\n" if ($name);
            $write_in .= "program=$program\n"  if ($program);
            $write_in .= "birthday=$dob\n" if ($dob);
            $write_in .= "home_suburb=$home\n" if ($home);
            $write_in .= "home_latitude=$lat\n"  if ($lat);
            $write_in .= "home_longitude=$long\n" if ($long);
            if ($new_password && ($new_password eq $re_password)) {
                $write_in .= "password=$new_password\n";
            } else {
                $write_in .= "password=$password\n";
            }
            $write_in .= $courses.$mates;
            print $f $write_in;
            close $f;
            if ($new_password ne $re_password) {
                print "<b><span style=\"color: red\">Passwords not match!</span></b>\n<p>\n";
            } else {
                print h2('Your changes are saved.');
            }
        } else {
            print "<b><span style=\"color: red\">Wrong password, try again.</span></b>\n<p>\n";
        }
    }
    open my $p, "$users_dir/$user/user.txt" or die "Can not open $users_dir/$user/user.txt: $!";
    my $mate_info = join '', <$p>;
    close $p;
    print start_form;
    print "<div class=\"post\"> <div class=\"edit_profile\"> \n";
    $mate_info =~ /full_name=(.*)/;
    print "Name", textarea(-name=>'name', -value=>$1, -maxlength=>"188"), p;
    $mate_info =~ /birthday=(.*)/;
    print "Date of Birth", textarea(-name=>'dob', -value=>$1, -maxlength=>"10"), p;
    $mate_info =~ /email=(.*)/;
    print "Email", textarea(-name=>'email', -value=>$1, -maxlength=>"188"), p;
    $mate_info =~ /program=(.*)/;
    print "Program", textarea(-name=>'program', -value=>$1, -maxlength=>"188"), p;
    $mate_info =~ /home_suburb=(.*)/;
    print "Home suburb", textarea(-name=>'home suburb', -value=>$1, -maxlength=>"188"), p;
    mate_info =~ /home_latitude=(.*)/;
    print "Home latitude", textarea(-name=>'home lat', -value=>$1, -maxlength=>"188"), p;
    mate_info =~ /home_longitude=(.*)/;
    print "Home longitude", textarea(-name=>'home long', -value=>$1, -maxlength=>"188"), p;
    print "Change password", "<input name=\"new_password\" type=\"password\" placeholder=\"password\" maxlength=\"188\"/>", p, "\n",
          "Confirm password", "<input name=\"re_password\" type=\"password\" placeholder=\"confirm password\" maxlength=\"188\"/>", p, "\n",
          "Type your current password to proceed:\n", p,
          "<input name=\"password\" type=\"password\" placeholder=\"current password\"/>\n", p,
          submit(-value => 'Submit', -name => "submit", -class=> 'mybutton'), "\n</div>\n</div>\n";
}

sub search {
    my ($search) = @_;
    $search =~ s/^\s+//g;
    $search =~ s/\s+$//g;
    print '<form method="post" action="?" id="search" enctype="multipart/form-data">', "\n",
           textfield(-name=>'search',-default=>'Search for Names', -value=>$search,-size=>50), "\n",
           '</form>', "\n", p;
    my $edited_search = quotemeta($search);
    if ($search) {
        #$search =~ s/&/&amp/g;
        #$search =~ s/\</&lt/g;
        #$search =~ s/\>/&gt/g;
        if ($search =~ /^z[0-9]{7}$/i) {
            if (-e glob("$users_dir/$search") and -d glob("$users_dir/$search")) {
                print h2("Search Results"), p;
                print start_form, "\n";
                if (-e glob("$users_dir/$search/profile.jpg")) {
                print image_button( -src=>"$users_dir/$search/profile.jpg", -name=>'view_profile',
                       -align=>'middle', -value=>"$search", -width=>"48", -height=>"48");
                } else {
                print image_button( -src=>$default_profile_img, -name=>'view_profile',
                       -align=>'middle', -value=>"$search", -width=>"48", -height=>"48");
                }
                my $full_name = get_name($search);
                print h2($full_name), "\n<p>\n";
                print end_form, "\n";
                
            } else {
                print "<b><span style=\"color: red\">Can not find this user: $search</span></b>\n<p>\n";
            }
        } else {
            for my $file (glob "$users_dir/*/user.txt") {
                open (my $p, $file) or die "Can not open $file: $!";
                my $mate_info = join '', <$p>;
                close $p;
                $mate_info =~ /full_name=(.*)/;
                my $full_name = $1;
                $mate_info =~ /zid=(.*)/;
                my $zid = $1;
                $zid_names{$zid} = $full_name;
            }
            for my $key (keys %zid_names) {
                if ($zid_names{$key} =~ /$edited_search/i) {
                    push @users_to_show, $key;
                } elsif ($search =~ /^z[0-9]+$/i && $key =~ /$edited_search/i) {
                    push @users_to_show, $key;
                }
            }
            if (@users_to_show) {
                print h2("Search Results"), p;
                print_mates(@users_to_show);
            } else {
                $search =~ s/&/&amp;/g;
                $search =~ s/</&lt;/g;
                $search =~ s/>/&gt;/g;
                print "<b><span style=\"color: red\">Can not find this user: $search</span></b>\n<p>\n";
            }
        }
    }
}

sub view_mates {
    my ($user_to_show)  = @_;
    if (-e glob("$users_dir/$user_to_show/user.txt")) {
        
        open my $p, "$users_dir/$user_to_show/user.txt" or die "Can not open $users_dir/$user_to_show/user.txt: $!";
        
        my $info = join '', <$p>;
        close $p;
        $info =~ /mates=\[(.*)\]/;
        my $mates = $1;
        my @mates = split /, /, $mates;
        print h2("Mates"), "\n";
        print_mates(@mates);
    }
}

sub print_mates {
    my (@mates) = @_;
    for my $mate (@mates) {
        print "<div class=\"mates\">\n", start_form, "\n";
        
        if (-e "$users_dir/$mate/profile.jpg") {
            print image_button( -src=>"$users_dir/$mate/profile.jpg", -name=>'view_profile',
                    -align=>'middle', -value=>"$mate", -width=>"48", -height=>"48");
        } else {
            print image_button( -src=>$default_profile_img, -name=>'view_profile',
                    -align=>'middle', -value=>"$mate", -width=>"48", -height=>"48");
        }
        open my $p, "$users_dir/$mate/user.txt" or die "Can not open $users_dir/$mate/user.txt: $!";
        my $mate_info = join '', <$p>;
        close $p;
        
        $mate_info =~ /full_name=(.*)/;
        my $full_name = $1;
        print h3($full_name), "\n<p>\n";
        print end_form, "</div>\n";
    }
}

sub log_out {
    my $delete = CGI::Cookie->new(  
                        -name    => 'ID',
                        -value   => '',
                        -expires => '-10d'
                        );
    print header(-cookie=>$delete),
          start_html(-title=>'Redirecting...',
                    -style => "matelook.css",
                    -head=>meta({-http_equiv => 'Refresh',
                    -content=> '3; matelook.cgi'}),
                    -BGCOLOR=>'#fbf6d9'
                    );
    print 'Thank you for using Matelook';
    print end_html;
}



#
# HTML placed at the top of every page
#
sub page_header {
    return <<eof
Content-Type: text/html;charset=utf-8

<!DOCTYPE html>
<html lang="en">
<head>
<title>Matelook</title>
<link href="matelook.css" rel="stylesheet">
</head>
<body>
<section id="color_bar"></section>
<section id="container" class="group">            
<header id="header">
<section id="mate_info">
<h1><a href="javascript:window.location.href=window.location.href">Matelook</a></h1>
</section>
<section id="mate_avatar">
<a href="javascript:window.location.href=window.location.href" class="avatar"><img src="$users_dir/$user/profile.jpg"></a>
</section>
</header>
<div id="wrap" style="margin-top: 0px; position: relative;">
eof
}

sub login_page_header {
return <<eof
Content-Type: text/html;charset=utf-8

<!DOCTYPE html>
<html lang="en">
<head>
<title>MateLook - Log in</title>
<link href="matelook.css" rel="stylesheet">
</head>
<body>
<section id="color_bar"></section>
<div class="login-page">
<div class="form">

eof
}


# from http://www.w3schools.com/howto/tryit.asp?filename=tryhow_css_modal2

sub login_failure {
return <<eof
<div class="modal-content">
  <div class="modal-header">
    <span class="close">×</span>
    <h2>Error</h2>
  </div>
  <div class="modal-body">
    <p>Username or password incorrect.</p>
  </div>
  <div class="modal-footer">
    <h3><a href=#>Forgot password?</a></h3>
  </div>
</div>
<script>
// Get the modal
var modal = document.getElementById('myModal');

// Get the button that opens the modal
var btn = document.getElementById("myBtn");

// Get the <span> element that closes the modal
var span = document.getElementsByClassName("close")[0];

// When the user clicks the button, open the modal
btn.onclick = function() {
    modal.style.display = "block";
}

// When the user clicks on <span> (x), close the modal
span.onclick = function() {
    modal.style.display = "none";
}

// When the user clicks anywhere outside of the modal, close it
window.onclick = function(event) {
    if (event.target == modal) {
        modal.style.display = "none";
    }
}
</script>
eof
}


#
# HTML placed at the bottom of every page
# It includes all supplied parameter values as a HTML comment
# if global variable $debug is set
#
sub page_trailer {
    my $html = "<div class=\"footer\">\n<p>&copy; 2016 <a href=\"http://www.google.com/\">Matelook</a></p>\n</div>\n</div>\n";
    $html .= join("", map("<!-- $_=".param($_)." -->\n", param())) if $debug;
    $html .= end_html;
    return $html;
}

main();
