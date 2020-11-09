#!/bin/bash
func="$(cat $1 | grep -P '[a-z]\=a\.split.*a\.join')"
echo $func

obfuscatedName="$(echo $func | grep -Poh '\(""\);[A-Za-z]+' | sed -s 's/("");//')"

obfuscatedFunc=$(cat "$1" | tr -d '\n' | grep -Poh "$obfuscatedName\=.*?}}")
mess="$(echo "$obfuscatedFunc" | grep -Poh "..:function\([a-z]+,[a-z]+\){var" | grep -Poh "^..")"
rev="$(echo "$obfuscatedFunc" |  grep -Poh "..:function\([a-z]+\){[a-z]+.rev" | grep -Poh "^..")"
splice="$(echo "$obfuscatedFunc" | grep -Poh "..:function\([a-z]+\,[a-z]+\){[a-z]+\." | grep -Poh "^..")"

echo "mess name: $mess"
echo "reverse name: $rev"
echo "splice name: $splice"

code="$(echo "$func" | sed -E 's/.*[a-z]+\.split\(""\);//;s/return.*//')"

IFS=';'
for i in $code; do
	num="$(echo "$i" | grep -Poh ',[0-9]+' | grep -Poh '[0-9]+')"
	if [[ "$i" == *"$splice"* ]]; then
		echo "a = a[$num:]"
	elif [[ "$i" == *"$rev"* ]]; then
		echo "a.reverse()"
	elif [[ "$i" == *"$mess"* ]]; then
		echo "a = self.mess(a, $num)"
	else 
		echo "UNKNOWN????"
	fi
done

echo --- and now, JS
for i in $code; do
	num="$(echo "$i" | grep -Poh ',[0-9]+' | grep -Poh '[0-9]+')"
	if [[ "$i" == *"$splice"* ]]; then
		echo "a.splice(0,$num)"
	elif [[ "$i" == *"$rev"* ]]; then
		echo "a.reverse()"
	elif [[ "$i" == *"$mess"* ]]; then
		echo "mess(a,$num)"
	else 
		echo "UNKNOWN????"
	fi
done