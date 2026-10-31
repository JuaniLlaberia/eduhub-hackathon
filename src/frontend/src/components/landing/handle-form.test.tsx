import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { HandleForm } from "./handle-form";

const push = vi.fn();
vi.mock("next/navigation", () => ({ useRouter: () => ({ push }) }));

beforeEach(() => push.mockReset());

describe("HandleForm", () => {
  it("sends a valid handle to the onboarding, normalized", async () => {
    render(<HandleForm />);
    await userEvent.type(screen.getByLabelText("Tu usuario de X"), "@Bilinkis");
    await userEvent.click(screen.getByRole("button", { name: "Analizar" }));
    expect(push).toHaveBeenCalledWith("/empezar?handle=bilinkis");
  });

  it("starts the onboarding from the first step when the field is empty", async () => {
    render(<HandleForm />);
    await userEvent.click(screen.getByRole("button", { name: "Analizar" }));
    expect(push).toHaveBeenCalledWith("/empezar");
  });

  it("does not navigate with an invalid handle and explains why", async () => {
    render(<HandleForm />);
    await userEvent.type(screen.getByLabelText("Tu usuario de X"), "no válido!");
    await userEvent.click(screen.getByRole("button", { name: "Analizar" }));
    expect(push).not.toHaveBeenCalled();
    expect(screen.getByRole("alert")).toHaveTextContent("Escribí un usuario de X válido.");
  });
});
