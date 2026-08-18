import path from 'path';
import fs from 'fs';
import fse from 'fs-extra';
import {
  backupName,
  execCommand,
  getTargetFile, TEMP_LOCATION,
} from './lib/config';
import { error } from './lib/log';

export const mkdir = (source: string) => {
  if (!fs.existsSync(path.dirname(source))) {
    fs.mkdirSync(path.dirname(source), { recursive: true });
  }
};

export const restoreFile = (source: string) => {
  mkdir(source);
  return Promise.resolve(fs.copyFileSync(
    getTargetFile(source),
    source,
  ));
};

export const restoreSqlite = (source: string) => {
  mkdir(source);
  return execCommand(
    [
      'sqlite3',
      `'${source}'`,
      `'.read ${getTargetFile(source)}'`,
    ],
  )
    .catch((e) => error(e));
};

export const restoreFolder = (source: string) => {
  const folder = path.dirname(source);
  mkdir(folder);
  return Promise.resolve(fse.copySync(getTargetFile(source), source));
};

export const restore = () => execCommand(
  [
    'tar',
    '-zxvf',
    backupName,
    '-C',
    TEMP_LOCATION,
  ],
);
