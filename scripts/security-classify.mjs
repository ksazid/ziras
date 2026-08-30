const files=process.argv.slice(2);
const sensitive=/(Identity|Authentication|Authorization|Payments|Uploads|Webhooks|Security|Migrations|infrastructure|release\.yml)/i;
const hits=files.filter(f=>sensitive.test(f));
console.log(JSON.stringify({codexSecurity:hits.length?'targeted':'skip',sensitivePaths:hits},null,2));
