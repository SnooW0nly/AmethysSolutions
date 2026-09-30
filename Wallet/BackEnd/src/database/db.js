import mongoose from "mongoose";
import { MONGODB_URI } from "../config/env.js";

let cached = global.mongoose || { conn: null, promise: null };
global.mongoose = cached;

export default async function dbConnect() {
  if (!MONGODB_URI) {
    throw new Error("MONGODB_URI não está definido no .env");
  }

  if (cached.conn) {
    return cached.conn;
  }

  if (!cached.promise) {
    const opts = {
      bufferCommands: false,
    };

    cached.promise = mongoose.connect(MONGODB_URI, opts).then((mongoose) => {
      console.log(`[${new Date().toISOString()}] ✓ MongoDB conectado`);
      return mongoose.connection;
    });
  }

  try {
    cached.conn = await cached.promise;
  } catch (e) {
    cached.promise = null;
    throw e;
  }

  return cached.conn;
}

