#include "word0196_equivalent.h"

#include <limits.h>
#include <string.h>

typedef struct {
    word0196_state *state;
    const word0196_replay_context *context;
    word0196_result *result;
} replay;

static uint8_t al(const word0196_state *state)
{
    return (uint8_t)(state->a & UINT16_C(0x00FF));
}

static void set_al(word0196_state *state, uint8_t value)
{
    state->a = (uint16_t)((state->a & UINT16_C(0xFF00)) | (uint16_t)value);
}

static void flag(word0196_state *state, uint16_t mask, bool value)
{
    state->psw = (uint16_t)((state->psw & (uint16_t)~mask) |
                          (value ? mask : UINT16_C(0)));
}

static void zero_flag(word0196_state *state, uint8_t value)
{
    flag(state, WORD0196_ZF, value == 0);
}

static uint16_t read_value(replay *run, uint16_t pc, uint16_t address,
                           uint8_t width_bits, uint16_t value)
{
    word0196_access *access = &run->result->accesses[run->result->access_count++];
    access->pc = pc;
    access->address = address;
    access->width_bits = width_bits;
    access->write = false;
    access->value = value;
    return value;
}

static uint8_t read_byte(replay *run, uint16_t pc, uint16_t address, uint8_t value)
{
    return (uint8_t)read_value(run, pc, address, 8, value);
}

static void write_byte(replay *run, uint16_t pc, uint16_t address,
                       uint8_t *destination, uint8_t value)
{
    word0196_write *write = &run->result->writes[run->result->write_count];
    word0196_access *access = &run->result->accesses[run->result->access_count++];
    write->pc = pc;
    write->address = address;
    write->width_bits = 8;
    write->old_value = *destination;
    write->new_value = value;
    write->event_index = run->context->event_index;
    write->write_ordinal = run->context->write_ordinal_base +
                           (uint32_t)run->result->write_count;
    run->result->write_count++;
    access->pc = pc;
    access->address = address;
    access->width_bits = 8;
    access->write = true;
    access->value = value;
    *destination = value;
}

static void finish_instruction(replay *run, uint16_t pc, uint16_t next_pc)
{
    word0196_step *step = &run->result->steps[run->result->step_count++];
    run->state->pc = next_pc;
    step->pc = pc;
    step->next_pc = next_pc;
    step->a = run->state->a;
    step->psw = run->state->psw;
}

static void load_al(word0196_state *state, uint8_t value)
{
    set_al(state, value);
    zero_flag(state, value);
    flag(state, WORD0196_DD, false);
}

word0196_status word0196_replay(word0196_state *state,
                              const word0196_replay_context *context,
                              word0196_result *result)
{
    replay run;
    uint8_t value, incoming_carry;
    uint16_t word;
    bool gate;

    if (state == NULL || context == NULL || result == NULL) {
        return WORD0196_INVALID_ARGUMENT;
    }
    if (state->pc != WORD0196_ENTRY_PC) {
        return WORD0196_UNSUPPORTED_ENTRY;
    }
    if (state->lrb != UINT16_C(0x0021)) {
        return WORD0196_UNKNOWN_MEMORY_CONTEXT;
    }
    if (state->halted) {
        return WORD0196_HALTED_INPUT;
    }
    if (context->write_ordinal_base > UINT32_MAX - WORD0196_MAX_WRITES) {
        return WORD0196_ORDINAL_OVERFLOW;
    }

    memset(result, 0, sizeof(*result));
    result->entry = *state;
    run.state = state;
    run.context = context;
    run.result = result;

    /* IR556F: LB A,off018E; byte load preserves AH/CF/HC/otherPSW, sets DD0/ZF. */
    value = read_byte(&run, 0x556F, 0x018E, state->ram018e);
    load_al(state, value);
    finish_instruction(&run, 0x556F, 0x5571);

    /* IR5571: SLLB A; logical byte shift, only CF written; AH/ZF/HC retained. */
    value = al(state);
    flag(state, WORD0196_CF, (value & UINT8_C(0x80)) != 0);
    set_al(state, (uint8_t)(((uint32_t)value * UINT32_C(2)) & UINT32_C(0xFF)));
    finish_instruction(&run, 0x5571, 0x5572);

    /* IR5572: ROLB off018E; incoming CF is the preceding shift's carry.
     * Read before write; keep even a numerically unchanged fresh write. */
    value = read_byte(&run, 0x5572, 0x018E, state->ram018e);
    incoming_carry = (uint8_t)((state->psw & WORD0196_CF) != 0);
    flag(state, WORD0196_CF, (value & UINT8_C(0x80)) != 0);
    value = (uint8_t)(((uint32_t)value * UINT32_C(2) + incoming_carry) & UINT32_C(0xFF));
    write_byte(&run, 0x5572, 0x018E, &state->ram018e, value);
    finish_instruction(&run, 0x5572, 0x5575);

    /* IR5575: LB A,r0. LRB0021 fixes r0's physical byte address0108. */
    value = read_byte(&run, 0x5575, 0x0108, state->local[0]);
    load_al(state, value);
    finish_instruction(&run, 0x5575, 0x5576);

    /* IR5576: DD0 ANDB A,off018E; only AL and ZF change. */
    value = read_byte(&run, 0x5576, 0x018E, state->ram018e);
    value = (uint8_t)(al(state) & value);
    set_al(state, value);
    zero_flag(state, value);
    finish_instruction(&run, 0x5576, 0x5578);

    /* IR5578: DD-independent word CMP RAM0196,#00C0. LE byte assembly;
     * no write, no accumulator change, no RAM00C0 access, HC/DD retained. */
    word = (uint16_t)((uint16_t)state->ram0196[0] |
                     (uint16_t)((uint16_t)state->ram0196[1] * UINT16_C(256)));
    word = read_value(&run, 0x5578, 0x0196, 16, word);
    result->compare_left = word;
    result->compare_right = UINT16_C(0x00C0);
    result->compare_cf = word < UINT16_C(0x00C0);
    result->compare_zf = word == UINT16_C(0x00C0);
    flag(state, WORD0196_CF, result->compare_cf);
    flag(state, WORD0196_ZF, result->compare_zf);
    finish_instruction(&run, 0x5578, 0x557D);

    /* IR557D: JLT consumes CF from CMP, with no intervening flag writer. */
    result->branch_taken = (state->psw & WORD0196_CF) != 0;
    finish_instruction(&run, 0x557D, result->branch_taken ? 0x55BF : 0x557F);

    if (result->branch_taken) {
        /* IR55BF/55C1/55C3: LB #0F, STB0117, STB018F. */
        load_al(state, UINT8_C(0x0F));
        finish_instruction(&run, 0x55BF, 0x55C1);
        write_byte(&run, 0x55C1, 0x0117, &state->ram0117, al(state));
        finish_instruction(&run, 0x55C1, 0x55C3);
        write_byte(&run, 0x55C3, 0x018F, &state->ram018f, al(state));
        finish_instruction(&run, 0x55C3, WORD0196_STOP_BELOW);
    } else {
        /* IR557F: preserve original0117 in localr1 BEFORE its RMW. */
        value = read_byte(&run, 0x557F, 0x0117, state->ram0117);
        write_byte(&run, 0x557F, 0x0109, &state->local[1], value);
        finish_instruction(&run, 0x557F, 0x5582);

        /* IR5582: byte memory AND with AL. */
        value = read_byte(&run, 0x5582, 0x0117, state->ram0117);
        value = (uint8_t)(value & al(state));
        write_byte(&run, 0x5582, 0x0117, &state->ram0117, value);
        zero_flag(state, value);
        finish_instruction(&run, 0x5582, 0x5585);

        /* IR5585/5588: genuine short-circuit native bit-test gates.
         * Gate0124 is not read if gate012A.7 already branches. */
        value = read_byte(&run, 0x5585, 0x012A, state->ram012a);
        gate = (value & UINT8_C(0x80)) != 0;
        finish_instruction(&run, 0x5585, gate ? 0x5592 : 0x5588);
        if (!gate) {
            value = read_byte(&run, 0x5588, 0x0124, state->ram0124);
            gate = (value & UINT8_C(0x20)) != 0;
            finish_instruction(&run, 0x5588, gate ? 0x5592 : 0x558B);
        }
        if (!gate) {
            /* IR558B/558E: branch-specific RMW effects, not dead stores. */
            value = read_byte(&run, 0x558B, 0x018F, state->ram018f);
            value = (uint8_t)(value & al(state));
            write_byte(&run, 0x558B, 0x018F, &state->ram018f, value);
            zero_flag(state, value);
            finish_instruction(&run, 0x558B, 0x558E);
            value = read_byte(&run, 0x558E, 0x012A, state->ram012a);
            value = (uint8_t)(value | UINT8_C(0x01));
            write_byte(&run, 0x558E, 0x012A, &state->ram012a, value);
            zero_flag(state, value);
            finish_instruction(&run, 0x558E, 0x5592);
        }

        /* IR5592/5594: LB018F then OR AL,#F0; AH and non-ZF flags retained. */
        value = read_byte(&run, 0x5592, 0x018F, state->ram018f);
        load_al(state, value);
        finish_instruction(&run, 0x5592, 0x5594);
        value = (uint8_t)(al(state) | UINT8_C(0xF0));
        set_al(state, value);
        zero_flag(state, value);
        finish_instruction(&run, 0x5594, WORD0196_STOP_NOT_BELOW);
    }

    result->final = *state;
    return WORD0196_OK;
}
