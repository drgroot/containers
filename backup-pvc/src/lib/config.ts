import fs from 'fs';
import { exec } from 'child_process';
import path from 'path';

export const MICROSERVICE_NAME = 'backup';

export const ISPROD = (process.env.NODE_ENV || '').toLowerCase() === 'production';

export const pathCleaner = (input: string) => input.replace(/[^A-Z.a-z0-0]+/g, '');

export const {
  SEPERATOR = ';',
  DATABASES = '',
  FILES = '',
  FOLDERS = '',
  TEMP_LOCATION = '/tmp/backup',
  TARGET_LOCATION = '/backup',
} = process.env;

export const backupName = path.join(TARGET_LOCATION, `${MICROSERVICE_NAME}.tar.gz`);

export const tempBackupLocation = path.join('/tmp', path.basename(backupName));

export const execCommand = (command: string[]): Promise<string> => new Promise(
  (resolve, reject) => {
    exec(command.join(' '), (error, stdout) => {
      if (error) {
        reject(error);
      } else {
        resolve(stdout);
      }
    });
  },
);

if (!fs.existsSync(TEMP_LOCATION)) {
  fs.mkdirSync(TEMP_LOCATION, { recursive: true });
}

export const getTargetFile = (source: string) => path.join(
  TEMP_LOCATION,
  pathCleaner(path.basename(source)),
);
