#!/usr/bin/perl
use strict;
use warnings;

my %pkgGroups = (
  '1' => [qw(
    vim-gtk rsync wget git openvpn
  )],
  '2' => [qw(
    libterm-readkey-perl
  )],
  '2' => [qw(
    x11vnc lsof
  )],
);

sub installPackages();

sub main(@){
  system "raspi", "-s", "apt-get update";
  system "raspi", "-s", "apt-get upgrade";
  installPackages();
}

sub installPackages(){
  print "\n\n";
  for my $pkgGroup(sort keys %pkgGroups){
    my @packages = @{$pkgGroups{$pkgGroup}}; 
    print "Installing group[$pkgGroup]:\n----\n@packages\n----\n";
    system "raspi", "-s", ''
      . " apt-get install"
      . " -y --allow-unauthenticated"
      . " @packages";
  }
}

&main(@ARGV);
