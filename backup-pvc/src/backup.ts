import fs from 'fs';
import fse from 'fs-extra';
import path from 'path';
import {
  execCommand,
  getTargetFile,
  tempBackupLocation,
  TEMP_LOCATION,
} from './lib/config';
import { mkdir } from './restore';

export const backupFile = (source: string) => {
  mkdir(getTargetFile(source));
  fs.copyFileSync(
    source,
    getTargetFile(source),
  );

  return Promise.resolve(true);
};

export const backupSqlite = (source: string) => {
  mkdir(getTargetFile(source));
  return execCommand(
    [
      'sqlite3',
      `'${source}'`,
      '.dump',
      '>',
      getTargetFile(source),
    ],
  );
};

export const backupFolder = (source: string) => {
  const folder = path.dirname(source);
  mkdir(getTargetFile(folder));

  return Promise.resolve(fse.copySync(source, getTargetFile(source)));
};

export const backup = (): Promise<any> => {
  if (fs.existsSync(tempBackupLocation)) {
    fs.unlinkSync(tempBackupLocation);
    return backup();
  }

  return execCommand(
    [
      'tar',
      '-czvf',
      tempBackupLocation,
      '-C',
      TEMP_LOCATION,
      '.',
    ],
  )
    .then(() => execCommand([
      'rm',
      '-rf',
      TEMP_LOCATION,
    ]));
};
