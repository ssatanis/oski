import { type ClassValue, clsx } from "clsx"
import { twMerge } from "tailwind-merge"

export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs))
}

export function getGradeColor(grade: number) {
  const colors = {
    0: "bg-red-100 text-red-800 border-red-200",
    1: "bg-orange-100 text-orange-800 border-orange-200",
    2: "bg-yellow-100 text-yellow-800 border-yellow-200",
    3: "bg-purple-100 text-purple-800 border-purple-200",
    4: "bg-green-100 text-green-800 border-green-200",
    5: "bg-emerald-100 text-emerald-800 border-emerald-200",
  }
  return colors[grade as keyof typeof colors] || colors[0]
}
