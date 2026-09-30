export interface User {
  id: string;
  username?: string;
  email?: string;
  avatar?: string;
  admin?: boolean;
  globalName?: string;
  applications: [];
  invoices: [];
}

export const names = [
    {
        tab: "/dashboard",
        title: "Você não tem aplicações para gerenciar",
        description: "Procuramos em todos os cantos e não encontramos nada. Tente criar uma aplicação para configurá-la.",
    },
    {
        tab: "/dashboard/invoices",
        title: "Você não tem faturas para gerenciar",
        description: "Procuramos em todos os cantos e não encontramos nada. Tente criar uma aplicação para renova-la.",
    }
];