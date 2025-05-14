#!/usr/bin/perl
use strict;
use warnings;
use File::Basename qw(basename);

sub prompt($$);
sub run(@);

my $IMG = "image_to_flash.img";
my $IMG_XZ = "$IMG.xz";

my $EXEC = basename $0;

my $USAGE = "Usage:
  $EXEC -h | --help
    show this message

  $EXEC
    flash $IMG using ddusb
      NOTE: runs lsblk and prompts before writing to block devices
";

sub main(@){
  while(@_ > 0){
    my $arg = shift @_;
    if($arg =~ /^(-h|--help)$/){
      print $USAGE;
      exit 0;
    }else{
      die "$USAGE\nERROR: unknown arg $arg\n";
    }
  }

  run "lsblk";
  print "\n\n";

  my $dev = prompt("ENTER BLOCK DEVICE OF SDCARD: ", "/dev/sdb");
  die "ERROR: \"$dev\" is not a block device\n" if not -b $dev;

  if(not -f $IMG and -f $IMG_XZ){
    print "echo decompressing $IMG_XZ\n";
    run "xz -d -k $IMG_XZ";
  }
  die "ERROR: missing $IMG\n" if not -f $IMG;

  if(promptYesNo("\nddusb $IMG $dev\nRUN THE ABOVE CMD?")){
    run "ddusb", $IMG, $dev;
  }
}

sub promptYesNo($){
  my ($msg) = @_;
  my $val = prompt("$msg [y/N] ", undef);
  if($val =~ /^(y|yes)$/i){
    return 1;
  }else{
    return 0;
  }
}

sub prompt($$){
  my ($msg, $default) = @_;
  $default = "" if not defined $default;

  $msg =~ s/'/'\\''/g;
  $msg =~ s/"/\\"/g;

  my $val = `bash -c 'read -p "$msg" -e -i "$default" PROMPT; echo "\$PROMPT"'`;
  chomp $val;
  $val =~ s/^\s*//;
  $val =~ s/\s*$//;

  if($val =~ /[ \t\r\n]/){
    die "ERROR: prompt for single value resulted in '$val'\n";
  }

  return $val;
}

sub run(@){
  print "@_\n";
  system @_;
  die "ERROR: command '@_' failed\n" if $? != 0;
}

&main(@ARGV);
