/**
 * Typed errors. Every error carries enough context to explain, in the report,
 * exactly which source failed and whether retrying could help.
 */

/** Base for everything this tool throws deliberately. */
export class MarketflowError extends Error {
  /** @param {string} message @param {{retryable?:boolean, cause?:unknown}} [opts] */
  constructor(message, opts = {}) {
    super(message, opts.cause !== undefined ? { cause: opts.cause } : undefined);
    this.name = new.target.name;
    this.retryable = opts.retryable === true;
  }
}

/** A response arrived but its shape was not what the vendor documents. */
export class ProviderParseError extends MarketflowError {
  /** @param {string} message @param {{providerId?:string, fieldPath?:string, cause?:unknown}} [opts] */
  constructor(message, opts = {}) {
    super(message, { retryable: false, cause: opts.cause });
    this.providerId = opts.providerId ?? null;
    this.fieldPath = opts.fieldPath ?? null;
  }
}

/** Transport-level or non-2xx failure. */
export class ProviderHttpError extends MarketflowError {
  /**
   * @param {string} message
   * @param {{providerId?:string, status?:number|null, url?:string|null,
   *          retryable?:boolean, retryAfterMs?:number|null, cause?:unknown}} [opts]
   */
  constructor(message, opts = {}) {
    // 408/429 and all 5xx are worth retrying; 4xx otherwise is a permanent answer.
    const status = opts.status ?? null;
    const inferred =
      status === null ? true : status === 408 || status === 429 || status >= 500;
    super(message, { retryable: opts.retryable ?? inferred, cause: opts.cause });
    this.providerId = opts.providerId ?? null;
    this.status = status;
    this.url = opts.url ?? null;
    this.retryAfterMs = opts.retryAfterMs ?? null;
  }
}

/** The vendor said "slow down" explicitly. Always retryable. */
export class RateLimitError extends ProviderHttpError {
  constructor(message, opts = {}) {
    super(message, { ...opts, retryable: true });
  }
}

/** Bad flags, bad config file, or a configuration that cannot work (exit code 2). */
export class ConfigError extends MarketflowError {
  constructor(message, opts = {}) {
    super(message, { retryable: false, cause: opts.cause });
  }
}
