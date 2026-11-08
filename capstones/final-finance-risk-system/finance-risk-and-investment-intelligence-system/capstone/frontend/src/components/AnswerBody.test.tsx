import { renderToStaticMarkup } from "react-dom/server";
import { describe, expect, it } from "vitest";
import { AnswerBody } from "./AnswerBody";

describe("AnswerBody", () => {
  it("renders a heading followed by bullets in the same block", () => {
    const html = renderToStaticMarkup(<AnswerBody text={"Intro line\n### Limits\n* **Sector:** below 25%\n* Regions: at least 3"} />);
    expect(html).toContain("<p><span>Intro line</span></p>");
    expect(html).toContain("<h3><span>Limits</span></h3>");
    expect(html).toContain("<ul><li><strong>Sector:</strong><span> below 25%</span></li><li><span>Regions: at least 3</span></li></ul>");
  });

  it("drops rule lines and lone italic markers", () => {
    const html = renderToStaticMarkup(<AnswerBody text={"---\n*Not investment advice.\nReview required.*"} />);
    expect(html).toContain("<hr/><p><span>Not investment advice.</span></p><p><span>Review required.</span></p>");
  });
});
