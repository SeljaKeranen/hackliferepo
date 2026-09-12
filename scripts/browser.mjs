import {chromium} from 'playwright';
import {existsSync} from 'node:fs';
export async function launch(){
 const env={...process.env};
 const root='/tmp/longview-browser-deps';
 if(existsSync(`${root}/fonts.conf`))env.FONTCONFIG_FILE=`${root}/fonts.conf`;
 if(existsSync(`${root}/root/usr/lib/x86_64-linux-gnu`))env.LD_LIBRARY_PATH=[`${root}/root/usr/lib/x86_64-linux-gnu`,`${process.env.HOME}/miniconda3/envs/rmg-env/lib`,process.env.LD_LIBRARY_PATH].filter(Boolean).join(':');
 return chromium.launch({headless:true,env});
}
