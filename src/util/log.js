/** Levelled logger. Everything goes to STDERR so that `--format json` on
 *  stdout stays machine-parseable when piped. */

const LEVELS = { silent: 0, error: 1, warn: 2, info: 3, debug: 4 };

/** @typedef {{error:Function, warn:Function, info:Function, debug:Function, level:string}} Logger */

export function createLogger({ level = 'info', color = false, stream = process.stderr } = {}) {
  const threshold = LEVELS[level] ?? LEVELS.info;
  const paint = (code, s) => (color ? `\x1b[${code}m${s}\x1b[0m` : s);
  const emit = (lvl, tag, args) => {
    if (LEVELS[lvl] > threshold) return;
    stream.write(`${tag} ${args.map(fmt).join(' ')}\n`);
  };
  return {
    level,
    error: (...a) => emit('error', paint('31', '[error]'), a),
    warn:  (...a) => emit('warn',  paint('33', '[warn ]'), a),
    info:  (...a) => emit('info',  paint('36', '[info ]'), a),
    debug: (...a) => emit('debug', paint('90', '[debug]'), a),
  };
}

function fmt(v) {
  if (typeof v === 'string') return v;
  if (v instanceof Error) return v.stack ?? `${v.name}: ${v.message}`;
  try { return JSON.stringify(v); } catch { return String(v); }
}

/** A logger that discards everything — for pure-function tests. */
export const silentLogger = createLogger({ level: 'silent' });
