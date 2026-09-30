/**
 * Funções de API para Metas
 */

import { getBalance } from './wallet';

export interface Goal {
  id: string;
  value: number; // em centavos
  label: string;
  completed: boolean;
  current: boolean;
  reward?: {
    type: 'trophy' | 'badge' | 'item';
    name: string;
    image?: string;
  };
}

export interface GoalsData {
  currentValue: number; // Total recebido em centavos
  currentGoal: Goal | null;
  nextGoal: Goal | null;
  completedGoals: Goal[];
  allGoals: Goal[];
  progress: {
    percentage: number;
    remaining: number;
  };
}

// Metas baseadas nas imagens - organizadas em grid 5x3
const GOALS_DEFINITION: Goal[] = [
  // Linha 1
  { id: '1', value: 0, label: 'Início', completed: false, current: false },
  { id: '2', value: 1000000, label: 'R$ 10K', completed: false, current: false }, // 10K em centavos = 1.000.000
  { id: '3', value: 2000000, label: 'R$ 20K', completed: false, current: false },
  { id: '4', value: 5000000, label: 'R$ 50K', completed: false, current: false, reward: { type: 'item', name: 'Conquista Bronze' } },
  { id: '5', value: 7500000, label: 'R$ 75K', completed: false, current: false },
  // Linha 2
  { id: '6', value: 37500000, label: 'R$ 375K', completed: false, current: false },
  { id: '7', value: 25000000, label: 'R$ 250K', completed: false, current: false },
  { id: '8', value: 10000000, label: 'R$ 100K', completed: false, current: false, reward: { type: 'badge', name: '100K FATURADOS' } },
  { id: '9', value: 10000000, label: 'R$ 100K', completed: false, current: false },
  { id: '10', value: 5000000, label: 'R$ 50K', completed: false, current: false },
  // Linha 3
  { id: '11', value: 50000000, label: 'R$ 500K', completed: false, current: false, reward: { type: 'badge', name: '500K FATURADOS' } },
  { id: '12', value: 50000000, label: 'R$ 500K', completed: false, current: false },
  { id: '13', value: 75000000, label: 'R$ 750K', completed: false, current: false },
  { id: '14', value: 100000000, label: 'R$ 1M', completed: false, current: false },
  { id: '15', value: 100000000, label: 'R$ 1M', completed: false, current: false, reward: { type: 'badge', name: '1M FATURADOS' } },
];

/**
 * Calcula o estado das metas baseado no valor atual
 */
export function calculateGoals(currentValue: number): GoalsData {
  // Ordenar metas por valor
  const sortedGoals = [...GOALS_DEFINITION].sort((a, b) => a.value - b.value);
  
  // Encontrar metas completadas
  const completedGoals = sortedGoals.filter(goal => currentValue >= goal.value);
  
  // Encontrar a meta atual (primeira não completada)
  const currentGoal = sortedGoals.find(goal => currentValue < goal.value) || null;
  
  // Encontrar próxima meta (mesma que atual, ou próxima após a atual)
  const currentIndex = currentGoal 
    ? sortedGoals.findIndex(g => g.id === currentGoal.id)
    : sortedGoals.length - 1;
  const nextGoal = sortedGoals[currentIndex + 1] || null;
  
  // Calcular progresso
  let progress = {
    percentage: 0,
    remaining: 0
  };
  
  if (currentGoal) {
    const previousGoal = sortedGoals[currentIndex - 1] || { value: 0 };
    const range = currentGoal.value - previousGoal.value;
    const progressInRange = currentValue - previousGoal.value;
    progress.percentage = Math.min(100, Math.max(0, (progressInRange / range) * 100));
    progress.remaining = currentGoal.value - currentValue;
  } else {
    // Todas as metas completadas
    const lastGoal = sortedGoals[sortedGoals.length - 1];
    progress.percentage = 100;
    progress.remaining = 0;
  }
  
  // Atualizar estado das metas
  const allGoals = GOALS_DEFINITION.map(goal => {
    const isCompleted = currentValue >= goal.value;
    const isCurrent = currentGoal?.id === goal.id;
    
    return {
      ...goal,
      completed: isCompleted,
      current: isCurrent
    };
  });
  
  return {
    currentValue,
    currentGoal,
    nextGoal,
    completedGoals,
    allGoals,
    progress
  };
}

/**
 * Busca dados de metas do usuário
 * IMPORTANTE: O cálculo de metas usa apenas ENTRADAS (pagamentos recebidos),
 * não inclui saques/transferências. Isso garante que as metas reflitam apenas
 * o faturamento/recebimentos do usuário.
 */
export async function getGoals(): Promise<GoalsData> {
  try {
    const balanceRes = await getBalance();
    // totalReceived: apenas pagamentos completados (entradas), não inclui saques
    const totalReceived = balanceRes.data.statistics.totalReceived || 0; // em centavos
    
    return calculateGoals(totalReceived);
  } catch (error) {
    console.error('Erro ao buscar metas:', error);
    // Retornar dados padrão em caso de erro
    return calculateGoals(0);
  }
}

