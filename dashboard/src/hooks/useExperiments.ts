/**
 * Custom Hooks for A/B Testing Experiments with React Query Caching
 */

import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { fetchExperiments, fetchExperimentDetail, stopExperiment } from '../services/api';
import type { Experiment } from '../types/index';

/**
 * Fetch list of experiments.
 */
export function useExperiments() {
  return useQuery({
    queryKey: ['experiments'],
    queryFn: fetchExperiments,
    staleTime: 2 * 60 * 1000, // 2 minutes
    gcTime: 10 * 60 * 1000, // 10 minutes cache
  });
}

/**
 * Fetch experiment detail by ID.
 */
export function useExperimentDetail(experimentId: string | null) {
  return useQuery({
    queryKey: ['experiments', experimentId],
    queryFn: () => {
      if (!experimentId) throw new Error('Experiment ID is required');
      return fetchExperimentDetail(experimentId);
    },
    staleTime: 60 * 1000, // 1 minute
    gcTime: 10 * 60 * 1000,
    enabled: !!experimentId,
  });
}

/**
 * Stop an experiment.
 */
export function useStopExperiment() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: stopExperiment,
    onSuccess: () => {
      // Invalidate experiments queries to refetch
      queryClient.invalidateQueries({ queryKey: ['experiments'] });
    },
  });
}
