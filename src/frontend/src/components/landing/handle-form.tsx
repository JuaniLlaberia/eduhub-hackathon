"use client";

// @handle form of the landing: validates the handle and opens the onboarding with it. Behavior: handle-form.test.tsx.
import { useRouter } from "next/navigation";
import { useState } from "react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";

const HANDLE = /^[a-z0-9_.]{1,30}$/;

export function HandleForm() {
  const router = useRouter();
  const [value, setValue] = useState("");
  const [error, setError] = useState("");

  function submit(event: React.FormEvent) {
    event.preventDefault();
    const handle = value.trim().replace(/^@/, "").toLowerCase();
    if (!handle) {
      router.push("/empezar");
      return;
    }
    if (!HANDLE.test(handle)) {
      setError("Escribí un usuario de X válido.");
      return;
    }
    setError("");
    router.push(`/empezar?handle=${handle}`);
  }

  return (
    <form className="flex w-full max-w-md flex-col gap-2" onSubmit={submit} noValidate>
      <div className="flex gap-2">
        <Input
          name="handle"
          value={value}
          onChange={(event) => setValue(event.target.value)}
          placeholder="@tucuenta"
          aria-label="Tu usuario de X"
          autoComplete="off"
        />
        <Button type="submit">Analizar</Button>
      </div>
      {error && (
        <p role="alert" className="text-destructive text-sm">
          {error}
        </p>
      )}
    </form>
  );
}
