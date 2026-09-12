import {readFileSync,writeFileSync,existsSync,mkdirSync} from 'node:fs';
import {execFileSync} from 'node:child_process';
import {createCipheriv,randomBytes,createHash} from 'node:crypto';
const packets=[];
for(const country of ['sweden','united-states','singapore']){
 const findings=JSON.parse(readFileSync(`eval/findings/${country}.json`));
 const provenance=JSON.parse(readFileSync(`eval/provenance/${country}.json`));
 packets.push({country,findings,provenance});
}
const benchmark=JSON.parse(readFileSync('eval/benchmark.json'));
const versions=JSON.parse(execFileSync('python3',['-m','scripts.review-versions'],{encoding:'utf8'}));
const body=JSON.stringify({packets,versions});
const packetId=createHash('sha256').update(body).digest('hex').slice(0,16);
mkdirSync('outputs',{recursive:true});
const keyPath='outputs/reviewer.key';
const key=existsSync(keyPath)?Buffer.from(readFileSync(keyPath,'utf8').trim(),'base64url'):randomBytes(32);
writeFileSync(keyPath,key.toString('base64url'),{mode:0o600});
const iv=randomBytes(12),cipher=createCipheriv('aes-256-gcm',key,iv);
const encrypted=Buffer.concat([cipher.update(body),cipher.final(),cipher.getAuthTag()]);
writeFileSync('public/review/packet.json',JSON.stringify({id:packetId,iv:iv.toString('base64'),ciphertext:encrypted.toString('base64')}));
console.log(`Encrypted reviewer packet ${packetId}: ${packets.reduce((n,p)=>n+p.findings.length,0)} candidates. Access key kept in ignored outputs/reviewer.key.`);
