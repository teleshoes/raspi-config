#!/usr/bin/perl
use strict;
use warnings;

my $sshDir = "$ENV{HOME}/.ssh";
my $host = `raspi`;
chomp $host;

sub run(@){
  print "@_\n";
  system @_;
  die "Error running \"@_\"\n" if $? != 0;
}

#makes the keys on the host, and appends to local .pub {local=>remote}
sub keygen($){
  my $user = shift;
  my $group = $user eq 'user' ? 'users' : $user;

  run 'ssh', "$user\@$host", "
    set -x
    mkdir -p ~/.ssh
    chmod go-w ~/.ssh
    chown $user.$group ~/
    rm ~/.ssh/*
    ssh-keygen -t rsa -N \"\" -q -f ~/.ssh/id_rsa
  ";

  run "ssh $user\@$host 'cat ~/.ssh/id_rsa.pub' >> $sshDir/$host.pub";
}

#copies the local pub keys and authorizes them {remote=>local}
sub keyCopy($){
  run "scp $sshDir/*.pub $_[0]\@$host:~/.ssh";
  run 'ssh', "$_[0]\@$host", "cat ~/.ssh/*.pub > ~/.ssh/authorized_keys";
}

sub main(@){
  die "Usage: $0\n" if @_ > 0;

  run 'rm', "-f", "$sshDir/$host.pub";
  print "default password is raspberry\n";
  print "\n\npasswd pi\n";
  run 'ssh', "pi\@$host", 'sudo passwd pi';
  print "\n\npasswd root\n";
  run 'ssh', "pi\@$host", 'sudo passwd root';

  print "permit root login on ssh\n";
  run 'ssh', "pi\@$host", "
    echo -ne '\\nchanging PermitRootLogin in sshd_config\\n\\n'
    echo -ne 'OLD: '
    grep '^PermitRootLogin ' /etc/ssh/sshd_config
    sudo sed -i 's/^PermitRootLogin .*/PermitRootLogin yes/' /etc/ssh/sshd_config
    echo -ne 'NEW: '
    grep '^PermitRootLogin ' /etc/ssh/sshd_config
  ";


  print "\n\nrestarting ssh\n";
  run 'ssh', "pi\@$host", "sudo service ssh restart &";

  my $ok = 0;
  my $delay = 3;
  my $attempts = 5;
  while(not $ok){
    my $sshIsUp = `ssh pi\@$host echo ssh-is-up`;
    $attempts--;
    chomp $sshIsUp;
    if($sshIsUp eq "ssh-is-up"){
      print "ssh is up!\n";
      $ok = 1;
    }else{
      if($attempts <= 0){
        die "max SSH attempts exceeded\n";
      }
      print "waiting ${delay}s to try again ($attempts attempts left)...\n";
      sleep $delay;
    }
  }


  keygen 'root';
  keygen 'pi';
  keyCopy 'root';
  keyCopy 'pi';

  run "cat $sshDir/*.pub > $sshDir/authorized_keys";
}

&main(@ARGV)
