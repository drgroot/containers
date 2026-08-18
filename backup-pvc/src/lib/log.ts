const print = (...any: any[]) => console.log(...any);

const CRITICAL = 'critical';
const ERROR = 'error';
const DEBUG = 'debug';
const INFO = 'info';
const WARN = 'warn';

const log = (level: string, ...messages: any[]): Promise<true> => {
  print(new Date(), level.toUpperCase(), ...messages);
  return Promise.resolve(true);
};

export const critical = (...args: any[]): Promise<true> => log(CRITICAL, ...args);
export const error = (...args: any[]): Promise<true> => log(ERROR, ...args);
export const debug = (...args: any[]): Promise<true> => log(DEBUG, ...args);
export const info = (...args: any[]): Promise<true> => log(INFO, ...args);
export const warn = (...args: any[]): Promise<true> => log(WARN, ...args);
