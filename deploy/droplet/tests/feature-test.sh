#!/bin/bash
# End-to-end feature matrix against the public AaaS URL.
U=https://168-144-216-83.sslip.io
K="X-API-Key: aaas_live_33333333333333333333333333333333"
D=/c/SUBARNAREKHA/system/apps/demo-sites
T=$(mktemp -d)
pass=0; fail=0
ok()  { echo "  PASS  $1"; pass=$((pass+1)); }
bad() { echo "  FAIL  $1"; fail=$((fail+1)); }

json() { # name path body-file expect-regex
  out=$(curl -s -m 120 -w '\n%{http_code} %{time_total}' -H "$K" -H "Content-Type: application/json; charset=utf-8" --data-binary @"$3" "$U$2")
  code=$(tail -1 <<<"$out" | cut -d' ' -f1); t=$(tail -1 <<<"$out" | cut -d' ' -f2)
  body=$(sed '$d' <<<"$out")
  if [ "$code" = 200 ] && grep -qE "$4" <<<"$body"; then ok "$1 (${t}s): $(cut -c1-90 <<<"$body")"; else bad "$1 [$code]: $(cut -c1-160 <<<"$body")"; fi
}

echo "== Translate"
printf '%s' '{"text":"The scholarship form must be submitted before the last date.","src_lang":"en","tgt_lang":"or"}' > $T/a.json
json "en->or" /translate/translate $T/a.json '"text":"[^"]*[଀-୿]'
printf '%s' '{"text":"ବୃତ୍ତି ପାଇଁ ଆବେଦନ ଶେଷ ତାରିଖ ପୂର୍ବରୁ ଦାଖଲ କରନ୍ତୁ।","src_lang":"or","tgt_lang":"en"}' > $T/b.json
json "or->en" /translate/translate $T/b.json '"text":"[A-Za-z]'
printf '%s' '{"text":"Bring your Aadhaar card to the camp.","src_lang":"en","tgt_lang":"hi"}' > $T/c.json
json "en->hi" /translate/translate $T/c.json '"text":"[^"]*[ऀ-ॿ]'

echo "== Easy Read"
printf '%s' '{"text":"Applicants are hereby requested to furnish the requisite documents forthwith.","lang":"en"}' > $T/d.json
json "simplify en" /translate/simplify $T/d.json '"text"'
printf '%s' '{"text":"ଆବେଦନକାରୀମାନଙ୍କୁ ଆବଶ୍ୟକ ଦସ୍ତାବିଜ ଦାଖଲ କରିବାକୁ ଅନୁରୋଧ କରାଯାଉଛି।","lang":"or"}' > $T/e.json
json "simplify or" /translate/simplify $T/e.json '"text"'

echo "== Read aloud (TTS)"
for l in or hi en; do
  case $l in
    or) txt='ନମସ୍କାର। ଏହି ପୃଷ୍ଠାକୁ ମୁଁ ପଢ଼ି ଶୁଣାଇବି।';;
    hi) txt='नमस्ते। मैं यह पृष्ठ पढ़कर सुनाऊँगा।';;
    en) txt='Hello. I will read this page aloud.';;
  esac
  printf '{"text":"%s","lang":"%s"}' "$txt" "$l" > $T/tts-$l.json
  r=$(curl -s -m 120 -o $T/tts-$l.wav -w '%{http_code} %{time_total} %{size_download} %{content_type}' -H "$K" -H "Content-Type: application/json; charset=utf-8" --data-binary @$T/tts-$l.json $U/tts/synthesise)
  set -- $r
  if [ "$1" = 200 ] && [ "$3" -gt 10000 ]; then ok "tts $l (${2}s, $3 bytes, $4)"; else bad "tts $l [$r] $(head -c 150 $T/tts-$l.wav)"; fi
done

echo "== Speak to fill (STT)"
out=$(curl -s -m 120 -w '\n%{http_code} %{time_total}' -H "$K" -F "audio=@$T/tts-or.wav;type=audio/wav" -F language=or $U/stt/transcribe)
code=$(tail -1 <<<"$out" | cut -d' ' -f1); body=$(sed '$d' <<<"$out")
[ "$code" = 200 ] && grep -q '"text":"[^"]' <<<"$body" && ok "stt or ($(tail -1 <<<"$out" | cut -d' ' -f2)s): $(cut -c1-90 <<<"$body")" || bad "stt or [$code]: $body"

echo "== Read document (OCR)"
for f in $D/*/assets/*.pdf $D/ssepd-odisha/assets/pension-notice-scan.png; do
  out=$(curl -s -m 120 -w '\n%{http_code} %{time_total}' -H "$K" -F "file=@$f" $U/translate/ocr)
  code=$(tail -1 <<<"$out" | cut -d' ' -f1); t=$(tail -1 <<<"$out" | cut -d' ' -f2); body=$(sed '$d' <<<"$out")
  n=$(grep -o '"text":"[^"]*' <<<"$body" | head -1 | wc -c)
  name=$(basename $(dirname $(dirname $f)))/$(basename $f)
  [ "$code" = 200 ] && [ "$n" -gt 60 ] && ok "ocr $name (${t}s, ${n} chars)" || bad "ocr $name [$code]: $(cut -c1-150 <<<"$body")"
done

echo "== Auth"
c=$(curl -s -o /dev/null -w %{http_code} -H "Content-Type: application/json" --data-binary @$T/a.json $U/translate/translate); [ "$c" = 401 ] && ok "no key -> 401" || bad "no key -> $c"
c=$(curl -s -o /dev/null -w %{http_code} -H "X-API-Key: aaas_live_deadbeefdeadbeefdeadbeefdeadbeef" -H "Content-Type: application/json" --data-binary @$T/a.json $U/translate/translate); [ "$c" = 401 ] && ok "bad key -> 401" || bad "bad key -> $c"

echo; echo "RESULT: $pass passed, $fail failed"
rm -rf $T
