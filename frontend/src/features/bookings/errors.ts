import { ApiError } from "@/api/client";

export function isConflict(error: unknown): error is ApiError {
  return error instanceof ApiError && error.status === 409;
}