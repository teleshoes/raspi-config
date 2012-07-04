#!/usr/bin/perl
use strict;
use warnings;

my $DIR = '/opt/CONFIG_FILES';
my $user = 'pi';
my $group = 'pi';

my @rsyncOpts = qw(
  -a  --no-owner --no-group
  --del
  --out-format=%n
);

sub handleFile($$){
  my ($src, $dest) = @_;
  $dest =~ s/%/\//g;
  my $destDir = `dirname $dest`;
  chomp $destDir;
  system "mkdir -p $destDir";
  print "\n%%% $dest\n";
  if(-d $src){
    system 'rsync', @rsyncOpts, "$src/", "$dest";
  }else{
    system 'rsync', @rsyncOpts, "$src", "$dest";
  }
  if($destDir =~ /^\/home\/pi/){
    system "chown -R $user.$group $dest";
    system "chown $user.$group $destDir";
  }else{
    system "chown -R root.root $dest";
    system "chown root.root $destDir";
  }
}

sub removeFile($){
  my $file = shift;
  if(-e $file){
    if(-d $file){
      $file =~ s/\/$//;
      $file .= '/';
      print "\nremoving these files in $file:\n";
      system "find $file";
    }else{
      print "\nremoving $file\n";
    }
    system "rm -r $file";
  }
}

for my $file(`ls -d $DIR/%*`){
  chomp $file;
  $file =~ s/^.*\///;
  my $src = "$DIR/$file";
  my $dest = $file;
  handleFile $src, $dest;
}

for my $file(`cat $DIR/config-files-to-remove`){
  chomp $file;
  removeFile $file;
}
