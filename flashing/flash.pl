#!/usr/bin/perl
use strict;
use warnings;
use File::Basename qw(basename);

sub prompt($$);
sub run(@);

my $IMG = "image_to_flash.img";
my $IMG_XZ = "$IMG.xz";

my $PART_IDX_BOOT="1";
my $PART_IDX_ROOT="2";

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

  if(promptYesNo("\n\nRUN \"ddusb $IMG $dev\"?")){
    run "ddusb", $IMG, $dev;
  }

  my $devBoot="${dev}${PART_IDX_BOOT}";
  my $devRoot="${dev}${PART_IDX_ROOT}";
  die "ERROR: \"$devBoot\" is not a block device\n" if not -b $devBoot;
  die "ERROR: \"$devRoot\" is not a block device\n" if not -b $devRoot;

  if(promptYesNo("\n\nRESIZE $devRoot root PARTITION?")){
    run "sudo parted -s -a opt $dev 'print free'";
    run "sudo parted -s -a opt $dev 'resizepart $PART_IDX_ROOT 100%'";
    run "sudo parted -s -a opt $dev 'print free'";

    run "sudo e2fsck -f $devRoot";
    run "sudo resize2fs $devRoot";

    run "sync";
  }

  if(promptYesNo("\n\nMOUNT /boot AND root PARTITIONS AND EDIT FILES?")){
    run "sudo mkdir -p boot";
    run "sudo mkdir -p root";
    run "sudo mount -t vfat $devBoot ./boot";
    run "sudo mount -t ext4 $devRoot ./root";

    run "sync";
    run "sleep 1";

    run "sudo umount ./boot";
    run "sudo umount ./root";
    run "sudo rmdir boot";
    run "sudo rmdir root";

    run "sync";
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
