#ifndef P28_WORD0196_EQUIVALENT_H
#define P28_WORD0196_EQUIVALENT_H

#include <stdbool.h>
#include <stddef.h>
#include <stdint.h>

/* Offline replay of reviewed software boundaries, not an ECU runtime or ABI. */
enum {
    WORD0196_ENTRY_PC = 0x556F,
    WORD0196_STOP_NOT_BELOW = 0x5596,
    WORD0196_STOP_BELOW = 0x55C5,
    WORD0196_MAX_STEPS = 15,
    WORD0196_MAX_WRITES = 5,
    WORD0196_MAX_ACCESSES = 17,
    WORD0196_CF = 0x8000,
    WORD0196_ZF = 0x4000,
    WORD0196_HC = 0x2000,
    WORD0196_DD = 0x1000
};

typedef struct {
    uint16_t a, psw, pc, lrb;
    uint16_t x1, x2, dp, usp, ssp;
    bool sf, halted;
    uint8_t local[8]; /* LRB0021 -> physical0108..010F, including r0/r1. */
    uint8_t ram0117, ram0124, ram0128, ram012a, ram018e, ram018f;
    uint8_t ram0196[2]; /* Explicit little-endian bytes, never host-word aliasing. */
} word0196_state;

typedef struct {
    uint32_t event_index, write_ordinal_base;
} word0196_replay_context; /* Imported offline annotation: NOT native proof. */

typedef struct {
    uint16_t pc, next_pc, a, psw;
} word0196_step;

typedef struct {
    uint16_t pc, address, value;
    uint8_t width_bits;
    bool write;
} word0196_access;

typedef struct {
    uint16_t pc, address;
    uint8_t width_bits, old_value, new_value;
    uint32_t event_index, write_ordinal;
} word0196_write;

typedef struct {
    word0196_state entry, final;
    uint16_t compare_left, compare_right;
    bool compare_cf, compare_zf, branch_taken;
    size_t step_count, access_count, write_count;
    word0196_step steps[WORD0196_MAX_STEPS];
    word0196_access accesses[WORD0196_MAX_ACCESSES];
    word0196_write writes[WORD0196_MAX_WRITES];
} word0196_result;

typedef enum {
    WORD0196_OK = 0,
    WORD0196_INVALID_ARGUMENT,
    WORD0196_UNSUPPORTED_ENTRY,
    WORD0196_UNKNOWN_MEMORY_CONTEXT,
    WORD0196_HALTED_INPUT,
    WORD0196_ORDINAL_OVERFLOW
} word0196_status;

/* Mutates state only after validating all incoming constraints. All writes,
 * even equal-value ones, are kept. No P2/SFR/timer/IRQ/clock effects exist.
 * Unknown/unrepresented RAM aliases are outside this compact contract.
 * state and result must be separate non-overlapping objects. */
word0196_status word0196_replay(word0196_state *state,
                              const word0196_replay_context *context,
                              word0196_result *result);

#endif
