import fs from 'fs';
import path from 'path';
import express from 'express';
import { backup } from './backup';
import { backupName, SEPERATOR, tempBackupLocation, TEMP_LOCATION } from './lib/config';
import methods from './methods';
import { restore, mkdir } from './restore';

const triggerRestore = () => restore()
  .then(async () => {
    for (const [items, methodObj] of Object.entries(methods)) {
      for (const item of items.split(SEPERATOR)) {
        if (item) {
          // eslint-disable-next-line no-await-in-loop
          await methodObj.restore(item);
        }
      }
    }
  });

const triggerBackup = async () => {
  for (const [items, methodObj] of Object.entries(methods)) {
    for (const item of items.split(SEPERATOR)) {
      if (item) {
        // eslint-disable-next-line no-await-in-loop
        await methodObj.backup(item);
      }
    }
  }

  await backup();
};

const app = express();

app.get('/restore', async (_req, res) => {
  if (!fs.existsSync(tempBackupLocation)) {
    await triggerBackup();
  }

  console.log('renaming backup');
  fs.renameSync(tempBackupLocation, backupName);

  console.log('triggering restore');
  mkdir(path.join(TEMP_LOCATION, 'data'));
  await triggerRestore();

  res.send('OK');
});

app.get('/', async (_req, res) => {
  await triggerBackup();
  res.sendFile(tempBackupLocation);
});

const start = () => app.listen(parseInt(process.env.PORT || '3000', 10));

if (require.main === module) {
  if (process.env.METHOD === 'SERVER' || process.env.SERVER) {
    start();
  } else {
    triggerRestore()
      .then(() => { process.exit(); });
  }
}

export default start;
