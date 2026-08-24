import { render, screen } from "@testing-library/react";
import App from "@/App";

test("App renders placeholder", () => {
  render(<App />);
  expect(screen.getByText(/Viz Graph/)).toBeInTheDocument();
  expect(screen.getByTestId("graph-view")).toBeInTheDocument();
  expect(screen.getByTestId("geo-map")).toBeInTheDocument();
  expect(screen.getByTestId("replay-slider")).toBeInTheDocument();
});
