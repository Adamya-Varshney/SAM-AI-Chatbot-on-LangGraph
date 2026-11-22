const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000"

export async function apiFetch<T>(
  path: string,
  token: string,
  options?: RequestInit,
): Promise<T> {
  const res = await fetch(`${API_URL}${path}`, {
    ...options,
    headers: {
      "Content-Type": "application/json",
      Authorization: `Bearer ${token}`,
      ...options?.headers,
    },
  })

  if (!res.ok) {
    const error = await res.json().catch(() => ({ error: { message: res.statusText } }))
    throw new Error(error.error?.message || res.statusText)
  }

  return res.json()
}
