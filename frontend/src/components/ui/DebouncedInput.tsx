import { useEffect, useRef, useState, type InputHTMLAttributes } from "react";

import { useDebounce } from "@/hooks/useDebounce";
import { Input } from "./Input";

/** Text input that commits its value to `onChange` after a debounce. Seeds once
 *  from `value`; intended for URL-synced list filters. */
export function DebouncedInput({
  value,
  onChange,
  delay = 300,
  ...props
}: {
  value: string;
  onChange: (value: string) => void;
  delay?: number;
} & Omit<InputHTMLAttributes<HTMLInputElement>, "value" | "onChange">) {
  const [local, setLocal] = useState(value);
  const debounced = useDebounce(local, delay);
  const first = useRef(true);

  useEffect(() => {
    if (first.current) {
      first.current = false;
      return;
    }
    onChange(debounced);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [debounced]);

  return <Input value={local} onChange={(e) => setLocal(e.target.value)} {...props} />;
}
