#!/usr/bin/perl
use strict;
use warnings;
use File::Basename qw(basename);

sub prompt($$);
sub run(@);
sub tryrun(@);

my $IMG_XZ = "image_to_flash.img.xz";

my $PART_IDX_BOOT="1";
my $PART_IDX_ROOT="2";

my $EXEC = basename $0;

my $USAGE = "Usage:
  $EXEC -h | --help
    show this message

  $EXEC
    flash $IMG_XZ using ddusb --xzcat
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

  if(promptYesNo("\n\nRUN \"ddusb --xzcat $IMG_XZ $dev\"?")){
    run "ddusb", "--xzcat", $IMG_XZ, $dev;
  }

  my $devBoot="${dev}${PART_IDX_BOOT}";
  my $devRoot="${dev}${PART_IDX_ROOT}";
  die "ERROR: \"$devBoot\" is not a block device\n" if not -b $devBoot;
  die "ERROR: \"$devRoot\" is not a block device\n" if not -b $devRoot;

  if(promptYesNo("\n\nRESIZE $devRoot root PARTITION?")){
    run "sudo parted -s -a opt $dev 'print free'";
    run "sudo parted -s -a opt $dev 'resizepart $PART_IDX_ROOT 100%'";
    run "sudo parted -s -a opt $dev 'print free'";

    #allow resize if no fsck errors, or all errors are fixed
    tryrun "sudo e2fsck -f $devRoot";
    my $exitCode = $? >> 8;
    print "fsck exit code: $exitCode\n";
    if($exitCode != 0 and $exitCode != 1){
      die "ERROR: fsck failed, not resizing\n";
    }
    run "sudo resize2fs $devRoot";

    run "sync";
  }

  if(promptYesNo("\n\nMOUNT /boot AND root PARTITIONS AND EDIT FILES?")){
    run "sudo mkdir -p boot";
    run "sudo mkdir -p root";
    run "sudo mount -t vfat $devBoot ./boot";
    run "sudo mount -t ext4 $devRoot ./root";

    #flag to enable sshd on first startup
    run "sudo touch ./boot/ssh";

    run "sudo ../setup-boot --local";

    run "sudo mkdir -p ./root/home/pi/.ssh/";
    run "sudo cp -ar ~/.ssh/authorized_keys ./root/home/pi/.ssh/";
    run "sudo chown -R --reference ~/.ssh/ ./root/home/pi/.ssh/";

    run "sudo mkdir -p ./root/root/.ssh/";
    run "sudo cp -ar ~/.ssh/authorized_keys ./root/root/.ssh/";
    run "sudo chown -R root:root ./root/root/.ssh/";

    run "sudo rm -f ./root/etc/ssh/sshd_config.d/rename_user.conf";

    run "sync";

    run "sleep 1";
    run "sudo umount ./boot";
    run "sudo umount ./root";
    run "sleep 1";

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
  tryrun(@_);
  die "ERROR: command '@_' failed\n" if $? != 0;
}
sub tryrun(@){
  print "@_\n";
  system @_;
}

&main(@ARGV);
