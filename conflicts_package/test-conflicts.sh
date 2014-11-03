#!/bin/bash
#Set of test for conflicts.sh
#	--no-update do not load repos from github
#	--cleanup delete repos over 50mb
#	conflicts=X, where X is an executable to test

MAX_REPO_SIZE_M=50

die()
{
	echo >&2 "$*"
	exit 1
}

forced_switch()
{
	git checkout -f $1 &>/dev/null
	git reset --hard origin/$1 &>/dev/null
	git clean -fd &>/dev/null
}

test_combination()
{
	local merge_target
	merge_target=`git branch | grep '*' | cut -d\  -f2`
	forced_switch $merge_target
	local conflicts_result
	if echo $conflicts | grep -q "conflicts.sh"; then $conflicts $@ ; else $conflicts origin/$merge_target $@ ; fi
	conflicts_result=$?
	forced_switch $merge_target
	local branch
	local merge_result
	for branch in $@ ; do git merge --no-ff -m "merge $branch" $branch &>/dev/null ; merge_result=$? ; done
	if [ "$merge_result" != "0" ] ; then merge_result="1" ; fi
	if [ "$merge_result" != "$conflicts_result" ] ; then echo "merge result $merge_result != $conflicts result $conflicts_result" ; exit 1 ; else return 0 ; fi
}

first_failing_combination()
{
	local branch
	(("$#" == 0)) && return 0
	for branch in $@
	do
		if ! git merge --no-ff -m "merge $branch" origin/$branch &>/dev/null || ! first_failing_combination $(local other_branch ; for other_branch in $@ ; do [ "$other_branch" != "$branch" ] && echo $other_branch ; done)
		then
			git reset --hard HEAD &>/dev/null
			git clean -fd &>/dev/null
			echo -n "$branch "
			return 1
		else
			git reset --hard HEAD^ &>/dev/null
			git clean -fd &>/dev/null
			return 0
		fi
	done
}

conflicts=$PWD/conflicts.py
for arg in $@ ; do if echo $arg | grep -q "conflicts=" ; then eval $arg ; echo Using $conflicts ; fi ; done
if test -x $PWD/$conflicts ; then conflicts=$PWD/$conflicts ; fi
if ! test -x $conflicts && ! which $conflicts; then die "$conflicts does not exists or does not have execution permissions" ; fi

mkdir -p tst && cd tst || die "cannot chdir to tst"

############### update repo collection
if ! echo $@ | grep -qe '--no-update'
then
	remotes=`wget -O- -q 'https://github.com/trending' | grep "class=\"repository-name" | awk -F\" '{print "https://github.com"$2".git"}'`
	if [ -z "$remotes" ] ; then die "error downloading repo list" ; fi
	for repo in $remotes ; do if git clone $repo &>/dev/null ; then echo $repo: cloned ; fi ; done
	for repo in * ; do cd $repo ; echo $PWD: updating repo ; forced_switch master ; git pull -a &>/dev/null ; cd .. ; done
fi

############### for each branch of each repo do tests
for repo in *
do
	cd $repo
	if ! [ -z `find -name "*.git*.lock"` ] ; then echo ">>> $repo: WARNING there are git lock files, skipping.." ; cd .. ; continue ; fi
	if (("`du -sm | cut -f1`" > "$MAX_REPO_SIZE_M" ))
	then
		cd ..
		if echo $@ | grep -qe '--cleanup'
		then
			echo ">>> $repo: WARNING repo size over $MAX_REPO_SIZE_M Mb, removing.."
			rm -fr $repo
		else
			echo ">>> $repo: WARNING repo size over $MAX_REPO_SIZE_M Mb, skipping.."
		fi
		continue
	fi
	branches=(`git branch -r | grep -v "HEAD ->" | grep -v '[0-9]' | awk -F'origin/' '{print $2$3}'`) #exclude release branches
	if ((${#branches[@]} < 3)) ; then echo ">>> $repo: too few branches in repo (need more than 2)" ; cd .. ; continue ; else echo ">>> $repo:" ; fi
	branch_index=0
	
	for branch in ${branches[@]}
	do
		other_branches=( ${branches[@]} )
		unset other_branches[$branch_index]
############### test 1: find all branches that can be automatically merged to $branch one by one. Look for merge sequence which produces merge error. Pass it to test
		echo -n "    $branch: "
		candidates=()
		for other_branch in ${other_branches[@]}
		do
			forced_switch $branch
			if git merge-base --octopus $branch $other_branch &>/dev/null && git merge --no-ff  -m "merge $other_branch" origin/$other_branch &>/dev/null ; then candidates+=( $other_branch ) ; fi
		done			
		if (("${#candidates[@]}" < 2))
		then
			echo "to few mergable braches for $branch (need more than one)"
		else
			forced_switch $branch
			combination=( `first_failing_combination ${candidates[@]}` )
			if [ -z "$combination" ]
			then
				echo "no failing combination of mergable branches"
			else
				to_test=''
				for (( idx=${#combination[@]}-1 ; idx>=0 ; idx-- ))
				do
					to_test="$to_test origin/${combination[idx]}"
				done
				echo "testing on failing combination: $to_test"
				test_combination $to_test
			fi
		fi
###############
		let branch_index++
	done
	cd ..
done
