#!/usr/bin/env node

import chalk from 'chalk';
import { PhotoManager } from './photoManager.js';

const manager = new PhotoManager();

manager.runPidUidIntakeSession({ interactive: false, continuous: true }).catch(error => {
  console.error(chalk.red('Photo watcher failed:'), error);
  process.exit(1);
});
