import math 
from typing import List, Dict, Tuple

import numpy as np
import matplotlib.pyplot as plt

def build_transition_matrix(
    action_labels_list: List[str], 
    action_label_to_id_map: Dict[str, int],
    allowed_successors_map: Dict[str, List[str]], 
    p_self: float = 0.5,
    epsilon_floor: float = 1e-9
):
    """Build a transition matrix for the Viterbi decoding.

    The transition matrix T is a square matrix where T[i, j] is the probability of moving 
    from the current action i to the next action j in a single time step.  
    
    Args:
        action_labels_list: The list of action label strings.
        action_label_to_id_map: Map from action label string to integer ID.
        allowed_successors_map: Dict where keys are actions and values are lists of allowed successor actions.
        p_self: The self-loop probability if self-transition is allowed and other transitions also exist.
        epsilon_floor: The minimum probability for any transition.
    """
    K = len(action_labels_list)
    T = np.zeros((K, K), dtype=float)

    for current_action in action_labels_list:
        i = action_label_to_id_map[current_action]

        current_action_allowed_successors = allowed_successors_map.get(current_action, [])
        valid_successors = [succ for succ in current_action_allowed_successors if succ in action_labels_list]
        
        is_self_an_allowed_successor = current_action in valid_successors 
        non_self_valid_successors = [succ for succ in valid_successors if succ != current_action]
        num_non_self_valid_successors = len(non_self_valid_successors)

        if not valid_successors: 
            # Case A: No allowed successors. Force self-loop with almost all probability.  
            for j_col_idx in range(K):
                if j_col_idx != i: 
                    T[i, j_col_idx] = epsilon_floor 
            
            T[i, i] = 1.0 - (K - 1) * epsilon_floor 
            
            if T[i, i] < epsilon_floor: 
                T[i, i] = epsilon_floor # Ensure self-loop is at least epsilon_floor

        elif is_self_an_allowed_successor and num_non_self_valid_successors == 0: 
            # Case B: Only self-transition is allowed. 
            for j_col_idx in range(K):
                if j_col_idx != i: 
                    T[i, j_col_idx] = epsilon_floor 

            T[i, i] = 1.0 - (K - 1) * epsilon_floor 

            if T[i, i] < epsilon_floor: 
                T[i, i] = epsilon_floor   

        elif is_self_an_allowed_successor and num_non_self_valid_successors > 0:
            # Case C: Self is allowed, others are allowed. 
            T[i, i] = p_self 
            prob_each_other_successor = (1.0 - p_self) / num_non_self_valid_successors 

            # Reset other unspecified transitions to epsilon before assigning specific probabilities. 
            for j_col_action_str in action_labels_list: 
                j_col_idx = action_label_to_id_map[j_col_action_str]
                if j_col_idx != i and j_col_action_str not in non_self_valid_successors: 
                    T[i, j_col_idx] = epsilon_floor 

            for succ in non_self_valid_successors:
                j_idx = action_label_to_id_map[succ]
                T[i, j_idx] = prob_each_other_successor 
                if T[i, j_idx] < epsilon_floor: 
                    T[i, j_idx] = epsilon_floor

        elif not is_self_an_allowed_successor and num_non_self_valid_successors > 0:
            # Case D: Self is not allowed, others are allowed.
            T[i, i] = epsilon_floor # Self-loop is just epsilon
            prob_each_other_successor = (1.0 - epsilon_floor) / num_non_self_valid_successors # Distribute almost 1.0
            
            for j_col_action_str in action_labels_list:
                 j_col_idx = action_label_to_id_map[j_col_action_str]
                 if j_col_idx != i and j_col_action_str not in non_self_valid_successors:
                     T[i, j_col_idx] = epsilon_floor

            for succ_str in non_self_valid_successors:
                j_idx = action_label_to_id_map[succ_str]
                T[i, j_idx] = prob_each_other_successor
                if T[i, j_idx] < epsilon_floor:
                    T[i, j_idx] = epsilon_floor

        elif not is_self_an_allowed_successor and num_non_self_valid_successors == 0:
            # Case E: Trap state. Not allowed to self-loop, not allowed to go elsewhere. Force self-loop.
            for j_col_idx in range(K):
                if j_col_idx != i:
                    T[i, j_col_idx] = epsilon_floor

            T[i, i] = 1.0 - (K - 1) * epsilon_floor

            if T[i, i] < epsilon_floor:
                T[i,i] = epsilon_floor
    
    # Normalize rows to ensure they sum to 1 
    row_sums = T.sum(axis=1, keepdims=True) 
    row_sums[row_sums < 1e-10] = 1.0  # Avoid division by zero
    T = T / row_sums
    return T 

def build_hard_emission_matrix(
    temporal_sequence: List[Tuple[str, Tuple[float, float]]], 
    action_label_to_id_map: Dict[str, int]
):
    """Build a S x K log-emission score matrix from the temporal sequence.
    The log-emission score matrix is defined as follows:
        - S: Number of segments in the temporal sequence.
        - K: Number of action labels. 

    The log-emission score matrix is initialized with -1e9 for all segments and action labels.
    For each segment in the temporal sequence, if the action label exists in the action_label_to_id_map,
    the corresponding entry in the log-emission score matrix is set to 0.

    Args:
        temporal_sequence: The input temporal sequence for temporal smoothing.
        action_label_to_id_map: Mapping from action label to index. 

    Returns:
        np.ndarray: Log score matrix of shape [num_segments x num_labels]. 
    """
    num_segments = len(temporal_sequence)
    num_action_labels = len(action_label_to_id_map)

    log_scores = np.full((num_segments, num_action_labels), -1e9, dtype=float)

    for i, (label, _) in enumerate(temporal_sequence):
        if label not in action_label_to_id_map:
            continue 

        k = action_label_to_id_map[label]
        log_scores[i, k] = 0 

    return log_scores

def build_soft_emission_matrix(
    temporal_sequence: List[Tuple[str, Tuple[float, float]]], # Updated type hint
    action_label_to_id_map: Dict[str, int],
    p_correct_emission: float = 0.8
):
    """Build a S x K log-emission score matrix with soft probabilities.

    This model allows for uncertainty in the observed labels.
    - S: Number of segments in the temporal sequence.
    - K: Number of action labels.

    The log-emission P(Observed_X_at_segment_t | True_State_k_at_segment_t) is defined as:
    - log(p_correct_emission) if k matches the ID of Observed_X_at_segment_t.
    - log(p_incorrect_emission) if k does not match, where p_incorrect_emission
      is (1 - p_correct_emission) / (K - 1).

    Args:
        temporal_sequence: The input temporal sequence (list of (label_string, timestamps)).
        action_label_to_id_map: Mapping from action label string to integer ID.
        p_correct_emission: The probability that the observed label is correct, given the
                           true state is the same as the observed label.

    Returns:
        np.ndarray: Log score matrix of shape [num_segments x num_action_labels].
    """
    num_segments = len(temporal_sequence)
    num_action_labels = len(action_label_to_id_map)

    if num_action_labels == 0:
        return np.array([]).reshape(num_segments, 0) # Handle empty vocabulary
    if num_segments == 0:
        return np.array([]).reshape(0, num_action_labels) # Handle empty sequence

    if not (0.0 < p_correct_emission <= 1.0):
        raise ValueError("p_correct_emission must be between 0 (exclusive) and 1 (inclusive).")

    if num_action_labels == 1:
        # If only one action label, emission must be for that label with p_correct_emission
        # and p_incorrect_emission is effectively irrelevant or could be considered 0.
        # The Viterbi algorithm will always pick this single state if p_correct_emission is high.
        log_prob_correct = math.log(p_correct_emission if p_correct_emission > 0 else 1e-12)
        log_prob_incorrect = -1e9 # Effectively impossible to observe something else
    else:
        p_incorrect_emission = (1.0 - p_correct_emission) / (num_action_labels - 1)
        log_prob_correct = math.log(p_correct_emission if p_correct_emission > 0 else 1e-12)
        log_prob_incorrect = math.log(p_incorrect_emission if p_incorrect_emission > 0 else 1e-12)
        if p_incorrect_emission <=0: # Handles p_correct_emission = 1.0
            log_prob_incorrect = -1e9


    # Initialize all scores as if the true state is different from the observed one
    # This will be overridden for the case where the true state matches the observation.
    # More accurately, we are calculating P(Observed_X | True_State_K) for each K.
    log_scores = np.full((num_segments, num_action_labels), log_prob_incorrect, dtype=float)


    for i, (observed_label_str, _) in enumerate(temporal_sequence):
        if observed_label_str not in action_label_to_id_map:
            # If label not in vocab, all its emission scores for this segment remain log_prob_incorrect
            # (meaning it's equally unlikely that any true state generated this unknown observation)
            continue

        id_of_observed_label = action_label_to_id_map[observed_label_str]

        for k_true_state_id in range(num_action_labels):
            if k_true_state_id == id_of_observed_label:
                # This is P(Observed_X | True_X)
                log_scores[i, k_true_state_id] = log_prob_correct
            else:
                # This is P(Observed_X | True_Y), where Y is k_true_state_id
                # and X is id_of_observed_label
                log_scores[i, k_true_state_id] = log_prob_incorrect

    return log_scores

def viterbi_decode(
    logPi: np.ndarray,  
    log_transition_matrix: np.ndarray, 
    log_emission_matrix: np.ndarray 
): 
    """
    Uses viterbi decoding to return the best path or most probable sequence of action labels.
    The goal is to enforce action order and transitions via the transition matrix.

    Args:
        logPi: The initial log-prob. This is a prior over possible starting action labels.
        log_transition_matrix: The log-transition matrix. This encodes transition likelihoods over all action pairs.
        log_emission_matrix: The log-emission matrix. Each row corresponds to a segment and each column corresponds to an action label.

    Returns:
        np.ndarray: This returns the 'best_path' which is the most probable sequence of action labels for the segments. 
                    The array contains a list of integers, each integer corresponds an action label in the action vocabulary.
    """
    T, K = log_emission_matrix.shape 
    V = np.full((T, K), -np.inf, dtype=float)
    backptr = np.zeros((T, K), dtype=int)

    # Initialization 
    V[0, :] = logPi + log_emission_matrix[0, :]
    backptr[0, :] = -1 

    # Recurrence 
    for t in range(1, T):
        for j in range(K):
            scores = V[t - 1, :] + log_transition_matrix[:, j]
            best_i = np.argmax(scores)
            V[t, j] = scores[best_i] + log_emission_matrix[t, j]
            backptr[t, j] = best_i 

    # Backtrack 
    best_path = np.zeros(T, dtype=int)
    best_path[T - 1] = np.argmax(V[T - 1, :])
    for t in range(T - 1, 0, -1):
        best_path[t - 1] = backptr[t, best_path[t]]
    
    return best_path 

def reconstruct_temporal_action_sequence(
    best_path_ids: np.ndarray,
    original_input_sequence: List[Tuple[str, Tuple[float, float]]],
    id_to_action_label_map: Dict[int, str],
    merge_consecutive: bool = True
) -> List[Tuple[str, Tuple[float, float]]]:
    """
    Reconstructs a temporal sequence of action labels and timestamps from the
    Viterbi decoded best path.

    Args:
        best_path_ids: A NumPy array of integer action IDs representing the
                       most probable sequence of states from Viterbi decoding.
                       Each ID corresponds to a segment in the original_input_sequence.
        original_input_sequence: The original temporal sequence that was fed
                                 (or corresponds to the observations fed) into
                                 the Viterbi model. This is a list of tuples,
                                 where each tuple is (original_label_str, (start_time, end_time)).
                                 The timestamps from this sequence are used.
        id_to_action_label_map: A dictionary mapping action integer IDs back
                                to their string labels.
        merge_consecutive: If True, consecutive segments with the same smoothed
                           action label will be merged into a single, longer segment.
                           If False, each original segment slot will have its
                           (potentially new) label and original timestamp.

    Returns:
        A list of tuples, where each tuple is (smoothed_action_label_str, (start_time, end_time)),
        representing the final smoothed temporal sequence.
    """
    if len(best_path_ids) != len(original_input_sequence):
        raise ValueError(
            "Length of best_path_ids must match the length of original_input_sequence."
        )

    # Step 1: Create the unmerged smoothed sequence with original timestamps
    unmerged_smoothed_sequence = []
    for i in range(len(best_path_ids)):
        smoothed_action_id = best_path_ids[i]
        
        # Get the string label for the smoothed ID
        smoothed_action_label_str = id_to_action_label_map.get(
            smoothed_action_id, f"UNKNOWN_ID_{smoothed_action_id}" # Fallback for unknown IDs
        )
        
        # Get the original timestamp for this segment position
        # The original_input_sequence provides the segment boundaries
        try:
            original_timestamp_tuple = original_input_sequence[i][1]
        except IndexError:
            # Should not happen if lengths match, but good for robustness
            raise IndexError(f"Could not retrieve timestamp for segment index {i} from original_input_sequence.")

        unmerged_smoothed_sequence.append(
            (smoothed_action_label_str, original_timestamp_tuple)
        )

    if not merge_consecutive:
        return unmerged_smoothed_sequence

    # Step 2: Merge consecutive identical labels if requested
    if not unmerged_smoothed_sequence: # Handle empty input
        return []

    final_merged_sequence = []
    
    current_label = unmerged_smoothed_sequence[0][0]
    current_start_time = unmerged_smoothed_sequence[0][1][0]
    # Initialize current_end_time with the end of the first segment
    current_end_time = unmerged_smoothed_sequence[0][1][1] 

    for i in range(1, len(unmerged_smoothed_sequence)):
        next_label = unmerged_smoothed_sequence[i][0]
        # The start time of the next segment isn't directly used for merging logic,
        # but its end time is.
        next_segment_start_time = unmerged_smoothed_sequence[i][1][0]
        next_segment_end_time = unmerged_smoothed_sequence[i][1][1]

        if next_label == current_label:
            # If the labels are the same, extend the current segment's end time
            # to the end time of this `next_segment`.
            # This handles cases with overlapping or gapped original segments appropriately.
            current_end_time = next_segment_end_time
        else:
            # Action changed, finalize the previous segment
            final_merged_sequence.append(
                (current_label, (current_start_time, current_end_time))
            )
            # Start a new segment
            current_label = next_label
            current_start_time = next_segment_start_time # Start time of the new distinct segment
            current_end_time = next_segment_end_time   # End time of this first part of the new segment
    
    # Add the last processed segment (either extended or newly started)
    final_merged_sequence.append(
        (current_label, (current_start_time, current_end_time))
    )
            
    return final_merged_sequence

def plot_viterbi_results(
    temporal_sequence: List[Tuple[str, Tuple[float, float]]],
    reconstructed_temporal_sequence: List[Tuple[str, Tuple[float, float]]],
    action_label_to_id_map: Dict[str, int],
    action_labels_list: List[str],
    video_duration: float,
    best_path: np.ndarray,
    num_segments: int,
    action_labels_count: int
):
    """
    Plots the results of the Viterbi decoding and the final smoothed temporal sequence.

    Args:
        temporal_sequence: The original temporal sequence with overlapping segments.
        reconstructed_temporal_sequence: The final smoothed temporal sequence after post-processing.
        action_label_to_id_map: Mapping from action label to index.
        action_labels_list: List of action labels.
        video_duration: Duration of the video in seconds.
        best_path: The best path obtained from Viterbi decoding.
    """
    fig, axs = plt.subplots(3, 1, figsize=(16, 20), sharex=True)
    time_axis = np.linspace(0, video_duration, num_segments)

    # Raw overlapping segments
    axs[0].set_title("1. Input: Raw Overlapping Segments")
    axs[0].set_ylabel("Actions")
    axs[0].set_yticks(range(action_labels_count))
    axs[0].set_yticklabels(action_labels_list)
    for lbl, (t0, t1) in temporal_sequence:
        axs[0].barh(action_label_to_id_map[lbl], t1 - t0, left=t0, height=0.6, color='skyblue', edgecolor='k')

    # Viterbi + median‐filtered frame labels
    axs[1].set_title("3. Viterbi Decoded Sequence (Frame labels over time)")
    axs[1].plot(time_axis, best_path, color='black')
    axs[1].set_ylabel("Class Index")

    # Final smoothed temporal sequence
    axs[2].set_title("4. Final Smoothed Temporal Sequence (After Post-Processing)")
    axs[2].set_ylabel("Actions")
    axs[2].set_yticks(range(action_labels_count))
    axs[2].set_yticklabels(action_labels_list)
    for lbl, (t0, t1) in reconstructed_temporal_sequence:
        axs[2].barh(action_label_to_id_map[lbl], t1 - t0, left=t0, height=0.6, color='lightcoral', edgecolor='k')

    axs[-1].set_xlabel("Time (seconds)")
    plt.tight_layout()
    plt.show()

if __name__ == "__main__":
    # Example usage
    action_labels = ["A", "B", "C"]
    action_to_id = {label: idx for idx, label in enumerate(action_labels)}
    allowed_successors = {
        "A": ["B", "C"],
        "B": ["A", "C"],
        "C": ["A"]
    }
    
    transition_matrix = build_transition_matrix(
        action_labels, 
        action_to_id, 
        allowed_successors, 
        p_self=0.5
    )
    
    print("Transition Matrix:\n", transition_matrix)

    temporal_sequence = [
        ("A", (0.0, 1.0)),
        ("C", (2.0, 3.0)),
        ("B", (1.0, 2.0)),
        ("A", (3.0, 4.0))
    ]

    emission_matrix = build_hard_emission_matrix(
        temporal_sequence, 
        action_to_id
    )
    print("Hard Emission Matrix:\n", emission_matrix)

    soft_emission_matrix = build_soft_emission_matrix(
        temporal_sequence, 
        action_to_id, 
        p_correct_emission=0.8
    )
    print("Soft Emission Matrix:\n", soft_emission_matrix)

    logPi = np.log(np.array([0.5, 0.3, 0.2]))  # Initial probabilities
    log_transition_matrix = np.log(transition_matrix)  # Transition probabilities
    log_emission_matrix = soft_emission_matrix  # Emission probabilities
    best_path = viterbi_decode(logPi, log_transition_matrix, log_emission_matrix)
    print("Best Path (Action Labels):", best_path)
    print("Best Path (Action IDs):", [action_labels[i] for i in best_path])

    temporal_sequence_reconstructed = reconstruct_temporal_sequence(
        best_path, 
        temporal_sequence, 
        {v: k for k, v in action_to_id.items()},
        merge_consecutive=True
    )
    print("Reconstructed Temporal Sequence:", temporal_sequence_reconstructed)

    # Plotting the results
    plot_viterbi_results(
        temporal_sequence,  
        temporal_sequence_reconstructed,
        action_to_id,
        action_labels,
        video_duration=4.0,
        best_path=best_path,
        num_segments=len(temporal_sequence),
        action_labels_count=len(action_labels)
    )
    