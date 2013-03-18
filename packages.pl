#!/usr/bin/perl
use strict;
use warnings;

my %pkgGroups = (
  '1' => [qw(
    vim-gtk rsync wget git openvpn
  )],
  '2' => [qw(
    libterm-readkey-perl libts-0.0
  )],
  '3' => [qw(
    x11vnc lsof psmisc zip unzip parted
  )],
  '4' => [qw(
    xinit openbox chromium-browser
  )],
  '5' => [qw(
    mplayer man
  )],
);

sub installPackages();

sub runOrDie(@){
  print "@_\n";
  system @_;
  die "Error running '@_'\n" if $? != 0;
}

sub main(@){
  runOrDie "raspi", "-b", "apt-get update";
  installPackages();
}

sub installPackages(){
  print "\n\n";
  for my $pkgGroup(sort keys %pkgGroups){
    my @packages = @{$pkgGroups{$pkgGroup}}; 
    print "Installing group[$pkgGroup]:\n----\n@packages\n----\n";
    runOrDie "raspi", "-b", ''
      . " apt-get install"
      . " -y --allow-unauthenticated"
      . " @packages";
  }
}

&main(@ARGV);
