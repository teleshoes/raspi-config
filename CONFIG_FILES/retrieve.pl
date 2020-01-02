#!/usr/bin/perl
use strict;
use warnings;

my $IPMAGIC_NAME = "raspi";

my $host = `ipmagic $IPMAGIC_NAME --host`;
my $user = "root";

sub main(@){
  die "Usage: $0 path [path path ..]\n" if @_ == 0 or $_[0] =~ /^(-h|--help)$/;
  chomp $host;
  for my $file(@_){
    my $boing = `boing $file`;
    chomp $boing;
    print "$file => $boing\n";
    system "rsync", "-avP", "$user\@$host:$file", $boing;
  }
}

&main(@ARGV);
