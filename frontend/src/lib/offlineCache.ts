const DB_NAME = "phantom.offlineCache.v1";
const STORE_NAME = "payloads";

export type CacheEnvelope<T> = {
  key: string;
  value: T;
  cached_at: string;
};

function openDb(): Promise<IDBDatabase> {
  return new Promise((resolve, reject) => {
    const request = indexedDB.open(DB_NAME, 1);
    request.onupgradeneeded = () => {
      request.result.createObjectStore(STORE_NAME, { keyPath: "key" });
    };
    request.onsuccess = () => resolve(request.result);
    request.onerror = () => reject(request.error);
  });
}

export async function cacheSet<T>(key: string, value: T): Promise<void> {
  const db = await openDb();
  await new Promise<void>((resolve, reject) => {
    const transaction = db.transaction(STORE_NAME, "readwrite");
    transaction.objectStore(STORE_NAME).put({ key, value, cached_at: new Date().toISOString() });
    transaction.oncomplete = () => resolve();
    transaction.onerror = () => reject(transaction.error);
  });
  db.close();
}

export async function cacheGet<T>(key: string): Promise<CacheEnvelope<T> | null> {
  const db = await openDb();
  const result = await new Promise<CacheEnvelope<T> | undefined>((resolve, reject) => {
    const transaction = db.transaction(STORE_NAME, "readonly");
    const request = transaction.objectStore(STORE_NAME).get(key);
    request.onsuccess = () => resolve(request.result as CacheEnvelope<T> | undefined);
    request.onerror = () => reject(request.error);
  });
  db.close();
  return result ?? null;
}

export function cacheKey(identitySub: string, resource: string, id = "default"): string {
  return `${identitySub}:${resource}:${id}`;
}
