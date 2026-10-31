import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { OnboardingFlow } from "./onboarding-flow";

const push = vi.fn();
const mutate = vi.fn();

vi.mock("next/navigation", () => ({ useRouter: () => ({ push }) }));
vi.mock("@/lib/api/queries", () => ({
  useCreateAnalysis: () => ({ mutate, isPending: false, error: null }),
}));

beforeEach(() => {
  push.mockReset();
  mutate.mockReset();
});

async function typeHandle(value: string) {
  await userEvent.type(screen.getByLabelText("Tu usuario"), value);
  await userEvent.click(screen.getByRole("button", { name: "Continuar" }));
}

describe("OnboardingFlow", () => {
  it("starts at step 1 of 4 asking for the X account", () => {
    render(<OnboardingFlow />);
    expect(screen.getByText("Paso 1 de 4")).toBeInTheDocument();
    expect(
      screen.getByRole("heading", { level: 1, name: "Empecemos por tu cuenta de X." }),
    ).toBeInTheDocument();
  });

  it("does not continue with an invalid handle", async () => {
    render(<OnboardingFlow />);
    await typeHandle("no válido!");
    expect(screen.getByText("Paso 1 de 4")).toBeInTheDocument();
    expect(screen.getByRole("alert")).toHaveTextContent("Escribí un usuario de X válido.");
  });

  it("sends the analysis without a brief when every brief step is skipped", async () => {
    render(<OnboardingFlow />);
    await typeHandle("@Demo_Finanzas");
    await userEvent.click(screen.getByRole("button", { name: "Omitir por ahora" }));
    await userEvent.click(screen.getByRole("button", { name: "Omitir por ahora" }));
    await userEvent.click(screen.getByRole("button", { name: "Omitir por ahora" }));
    expect(mutate).toHaveBeenCalledWith(
      { handle: "demo_finanzas", max_posts: 200, context: null },
      expect.objectContaining({ onSuccess: expect.any(Function) }),
    );
  });

  it("sends the brief it builds and goes to the analysis screen", async () => {
    render(<OnboardingFlow />);
    await typeHandle("demo_finanzas");
    await userEvent.click(screen.getByRole("radio", { name: "Vender un producto o servicio" }));
    expect(screen.getByLabelText("Así te va a leer NOVA")).toHaveTextContent(
      "Publicás para vender un producto o servicio.",
    );
    await userEvent.click(screen.getByRole("button", { name: "Continuar" }));
    await userEvent.click(screen.getByRole("checkbox", { name: "18 a 29 años" }));
    await userEvent.click(screen.getByRole("button", { name: "Continuar" }));
    await userEvent.click(screen.getByRole("radio", { name: "Que entren a un link" }));
    await userEvent.click(screen.getByRole("button", { name: "Analizar mi cuenta" }));
    expect(mutate).toHaveBeenCalledWith(
      {
        handle: "demo_finanzas",
        max_posts: 200,
        context: {
          goal: "sell",
          audience_filters: { age_groups: ["18 a 29 años"], genders: [], provinces: [] },
          preferred_cta: "link",
        },
      },
      expect.anything(),
    );
    const { onSuccess } = mutate.mock.calls[0][1];
    onSuccess({ id: "job-1" });
    expect(push).toHaveBeenCalledWith("/analisis/job-1");
  });

  it("can start with a known handle at a later step, to edit the brief", () => {
    render(<OnboardingFlow initialHandle="demo_finanzas" initialStep={2} />);
    expect(screen.getByText("Paso 2 de 4")).toBeInTheDocument();
    expect(screen.getByRole("heading", { level: 1, name: "¿Para qué publicás?" })).toBeInTheDocument();
  });
});
