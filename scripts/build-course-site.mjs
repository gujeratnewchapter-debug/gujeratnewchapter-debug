import { copyFile, mkdir } from "node:fs/promises";
import { resolve } from "node:path";

const root = process.cwd();
const output = resolve(root, "course-site", "dist");

await mkdir(output, { recursive: true });
await copyFile(
  resolve(root, "course-site", "index.html"),
  resolve(output, "index.html"),
);
await copyFile(
  resolve(root, "Business_Plan_Development_Course_and_Module_1_Lesson_1.md"),
  resolve(output, "course.md"),
);

console.log("Built the Business Plan Development course site.");
