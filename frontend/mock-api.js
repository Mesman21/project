import { categories, validationError } from "./src/common.js";

const seed = [
  ["Де можна переглянути розклад занять?", "information_request", "train"],
  ["Після входу сторінка залишається порожньою.", "incident_report", "train"],
  ["Було б зручно отримувати сповіщення про зміни розкладу.", "suggestion", "test"],
  ["Коли відбудеться наступна консультація?", "information_request", "test"],
];

function send(response, status, data = null) {
  response.writeHead(status, {
    "Content-Type": "application/json; charset=utf-8",
    "Cache-Control": "no-store",
  });
  response.end(status === 204 ? undefined : JSON.stringify(data));
}

async function readBody(request) {
  const chunks = [];
  let size = 0;
  for await (const chunk of request) {
    size += chunk.length;
    if (size > 32768) throw new Error("Запит завеликий.");
    chunks.push(chunk);
  }
  return JSON.parse(Buffer.concat(chunks).toString("utf8"));
}

function categoryFor(text) {
  const value = text.toLocaleLowerCase("uk");
  if (/збій|помилк|не відкрива|порожн[яью]/u.test(value)) return "incident_report";
  if (/пропону|було б|додайте|варто/u.test(value)) return "suggestion";
  return "information_request";
}

export function mockApi() {
  const examples = seed.map(([text, category_code, dataset_split], index) => ({
    message_id: index + 1, text, category_code, dataset_split, locked: false,
  }));
  let nextId = examples.length + 1;

  async function handle(request, response, path) {
    const method = request.method;
    if (method === "POST" && path === "/api/classify") {
      const data = await readBody(request);
      const error = typeof data?.text === "string"
        ? validationError(data.text) : "Введіть текст повідомлення.";
      if (error) return send(response, 422, { detail: error });
      const code = categoryFor(data.text);
      return send(response, 200, { category_code: code, category_name: categories[code] });
    }

    if (method === "GET" && path === "/api/statistics") {
      const counts = [6, 4, 2];
      return send(response, 200, {
        total: 12,
        categories: Object.entries(categories).map(([category_code, category_name], i) => ({
          category_code, category_name, count: counts[i], share: counts[i] / 12,
        })),
      });
    }

    if (method === "GET" && path === "/api/examples") {
      return send(response, 200, examples.toReversed());
    }

    const match = path.match(/^\/api\/examples\/(\d+)$/u);
    const index = match ? examples.findIndex(item => item.message_id === Number(match[1])) : -1;
    if (match && index === -1) return send(response, 404, { detail: "Приклад не знайдено." });
    if (match && method === "DELETE") {
      examples.splice(index, 1);
      return send(response, 204);
    }

    if ((path === "/api/examples" && method === "POST") || (match && method === "PUT")) {
      const data = await readBody(request);
      const error = typeof data?.text === "string"
        ? validationError(data.text) : "Введіть текст повідомлення.";
      if (error) return send(response, 422, { detail: error });
      if (!Object.hasOwn(categories, data.category_code) || !["train", "test"].includes(data.dataset_split)) {
        return send(response, 422, { detail: "Перевірте категорію та вибірку." });
      }
      const text = data.text.trim();
      if (examples.some((item, i) => item.text === text && i !== index)) {
        return send(response, 409, { detail: "Такий текст уже є у списку." });
      }
      const item = {
        message_id: match ? examples[index].message_id : nextId++,
        text,
        category_code: data.category_code,
        dataset_split: data.dataset_split,
        locked: false,
      };
      if (match) examples[index] = item;
      else examples.push(item);
      return send(response, match ? 200 : 201, item);
    }

    return send(response, 404, { detail: "Сценарій не знайдено." });
  }

  return {
    name: "classifier-mock-api",
    configureServer(server) {
      server.middlewares.use((request, response, next) => {
        const path = new URL(request.url, "http://127.0.0.1").pathname;
        if (!path.startsWith("/api/")) return next();
        handle(request, response, path).catch(() => {
          send(response, 422, { detail: "Перевірте формат запиту." });
        });
      });
    },
  };
}
