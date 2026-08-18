import { backupFile, backupFolder, backupSqlite } from './backup';
import { DATABASES, FILES, FOLDERS } from './lib/config';
import { restoreFile, restoreFolder, restoreSqlite } from './restore';

export interface BACKUP {
  backup: (i: string) => Promise<any>
  restore: (i: string) => Promise<any>
}

const methods: { [key: string]: BACKUP } = {
  [FILES]: {
    backup: backupFile,
    restore: restoreFile,
  },
  [DATABASES]: {
    backup: backupSqlite,
    restore: restoreSqlite,
  },
  [FOLDERS]: {
    backup: backupFolder,
    restore: restoreFolder,
  },
};

export default methods;
