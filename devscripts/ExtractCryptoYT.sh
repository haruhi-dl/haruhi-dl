#!/bin/bash
data="$(curl -s "https://www.youtube.com/s/player/$1/player_ias.vflset/en_GB/base.js")"
func="$(grep -P '[a-z]\=a\.split.*a\.join' <<< "$data")"
echo "full extracted function: $func"

obfuscatedName="$(grep -Poh '\(""\);[A-Za-z]+' <<< "$func" | sed -s 's/("");//')"

obfuscatedFunc=$(tr -d '\n' <<< "$data" | grep -Poh "$obfuscatedName\=.*?}}")
mess="$(grep -Poh "..:function\([a-z]+,[a-z]+\){var" <<< "$obfuscatedFunc" | grep -Poh "^..")"
rev="$(grep -Poh "..:function\([a-z]+\){[a-z]+.rev" <<< "$obfuscatedFunc" | grep -Poh "^..")"
splice="$(grep -Poh "..:function\([a-z]+\,[a-z]+\){[a-z]+\." <<< "$obfuscatedFunc" | grep -Poh "^..")"

echo "mess name: $mess"
echo "reverse name: $rev"
echo "splice name: $splice"

code="$(sed -E 's/.*[a-z]+\.split\(""\);//;s/return.*//' <<< "$func")"

echo "---"

IFS=';'
for i in $code; do
	num="$(grep -Poh ',[0-9]+' <<< "$i" | grep -Poh '[0-9]+')"
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

echo "--- and now, JS"
for i in $code; do
	num="$(grep -Poh ',[0-9]+' <<< "$i" | grep -Poh '[0-9]+')"
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
