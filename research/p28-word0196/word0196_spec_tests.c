#include "word0196_equivalent.h"

#include <stdio.h>
#include <string.h>

static uint32_t checked_vectors;
static uint32_t checked_repeated;
static uint32_t checked_negative;

#define REQUIRE(test) do { if (!(test)) { \
    fprintf(stderr, "Specification failure at line %u, vector %u\n", \
            (unsigned)__LINE__, (unsigned)checked_vectors); return false; \
} } while (0)

/* Independent bit placement, not the implementation's multiply/truncate path. */
static uint8_t rotate_spec(uint8_t value)
{
    uint32_t result = 0;
    unsigned bit;
    for (bit = 0; bit < 8; ++bit) {
        if ((value & (UINT32_C(1) << bit)) != 0) {
            result |= UINT32_C(1) << ((bit + 1U) % 8U);
        }
    }
    return (uint8_t)result;
}

static bool state_equal(const word0196_state *a, const word0196_state *b)
{
    return a->a == b->a && a->psw == b->psw && a->pc == b->pc && a->lrb == b->lrb &&
        a->x1 == b->x1 && a->x2 == b->x2 && a->dp == b->dp && a->usp == b->usp &&
        a->ssp == b->ssp && a->sf == b->sf && a->halted == b->halted &&
        memcmp(a->local, b->local, sizeof(a->local)) == 0 &&
        a->ram0117 == b->ram0117 && a->ram0124 == b->ram0124 &&
        a->ram0128 == b->ram0128 && a->ram012a == b->ram012a &&
        a->ram018e == b->ram018e && a->ram018f == b->ram018f &&
        memcmp(a->ram0196, b->ram0196, sizeof(a->ram0196)) == 0;
}

static bool check_vector(word0196_state initial, uint32_t ordinal, uint32_t event,
                         word0196_state *outgoing)
{
    word0196_state actual = initial, expected = initial;
    word0196_replay_context context = {event, ordinal};
    word0196_result result;
    uint16_t word = (uint16_t)((uint32_t)initial.ram0196[1] * 256U + initial.ram0196[0]);
    uint8_t rotated = rotate_spec(initial.ram018e);
    uint8_t mask = (uint8_t)(rotated & initial.local[0]);
    bool below = word <= UINT16_C(0x00BF);
    bool first_gate = (initial.ram012a / UINT8_C(128)) != 0;
    bool second_gate = ((initial.ram0124 / UINT8_C(32)) % UINT8_C(2)) != 0;
    bool bypass = first_gate || second_gate;
    size_t i, expected_steps = below ? 10U : first_gate ? 12U : second_gate ? 13U : 15U;
    static const uint16_t common_path[] = {0x556F,0x5571,0x5572,0x5575,0x5576,0x5578,0x557D};
    static const uint16_t below_path[] = {0x55BF,0x55C1,0x55C3};
    static const uint16_t above_prefix[] = {0x557F,0x5582,0x5585};
    uint16_t paths[WORD0196_MAX_STEPS];
    size_t path_count = 0;

    ++checked_vectors;
    expected.ram018e = rotated;
    expected.psw = (uint16_t)(initial.psw & UINT16_C(0x0FFF));
    if ((initial.psw & WORD0196_HC) != 0) { expected.psw |= WORD0196_HC; }
    if (below) {
        expected.pc = WORD0196_STOP_BELOW;
        expected.a = (uint16_t)((initial.a & UINT16_C(0xFF00)) + UINT16_C(15));
        expected.ram0117 = 15;
        expected.ram018f = 15;
        expected.psw |= WORD0196_CF;
    } else {
        expected.pc = WORD0196_STOP_NOT_BELOW;
        expected.local[1] = initial.ram0117;
        expected.ram0117 = (uint8_t)(initial.ram0117 & mask);
        if (!bypass) {
            expected.ram018f = (uint8_t)(initial.ram018f & mask);
            expected.ram012a = (uint8_t)(initial.ram012a | UINT8_C(1));
        }
        expected.a = (uint16_t)((initial.a & UINT16_C(0xFF00)) +
                               (uint16_t)(expected.ram018f | UINT8_C(0xF0)));
    }

    REQUIRE(word0196_replay(&actual, &context, &result) == WORD0196_OK);
    REQUIRE(state_equal(&actual, &expected));
    REQUIRE(state_equal(&result.entry, &initial));
    REQUIRE(state_equal(&result.final, &expected));
    REQUIRE(result.branch_taken == below && result.compare_cf == below);
    REQUIRE(result.compare_zf == (word == UINT16_C(192)));
    REQUIRE(result.compare_left == word && result.compare_right == UINT16_C(192));
    REQUIRE(result.step_count == expected_steps);
    REQUIRE(result.write_count == (below ? 3U : bypass ? 3U : 5U));
    REQUIRE(result.access_count == (below ? 8U : first_gate ? 12U : second_gate ? 13U : 17U));
    for (i = 0; i < sizeof(common_path)/sizeof(common_path[0]); ++i) { paths[path_count++] = common_path[i]; }
    if (below) {
        for (i = 0; i < sizeof(below_path)/sizeof(below_path[0]); ++i) { paths[path_count++] = below_path[i]; }
    } else {
        for (i = 0; i < sizeof(above_prefix)/sizeof(above_prefix[0]); ++i) { paths[path_count++] = above_prefix[i]; }
        if (!first_gate) { paths[path_count++] = 0x5588; }
        if (!bypass) { paths[path_count++] = 0x558B; paths[path_count++] = 0x558E; }
        paths[path_count++] = 0x5592; paths[path_count++] = 0x5594;
    }
    REQUIRE(path_count == result.step_count);
    for (i = 0; i < path_count; ++i) {
        REQUIRE(result.steps[i].pc == paths[i]);
        REQUIRE(result.steps[i].next_pc == (i + 1U < path_count ? paths[i+1U] : expected.pc));
        REQUIRE((result.steps[i].a & UINT16_C(0xFF00)) == (initial.a & UINT16_C(0xFF00)));
        REQUIRE((result.steps[i].psw & WORD0196_HC) == (initial.psw & WORD0196_HC));
        REQUIRE((result.steps[i].psw & WORD0196_DD) == 0);
        REQUIRE((result.steps[i].psw & UINT16_C(0x0FFF)) == (initial.psw & UINT16_C(0x0FFF)));
    }
    REQUIRE(result.steps[0].a == (uint16_t)((initial.a & UINT16_C(0xFF00)) | initial.ram018e));
    REQUIRE((result.steps[0].psw & WORD0196_ZF) == (initial.ram018e == 0 ? WORD0196_ZF : 0));
    REQUIRE((result.steps[1].psw & WORD0196_ZF) == (result.steps[0].psw & WORD0196_ZF));
    REQUIRE((result.steps[2].psw & (WORD0196_ZF|WORD0196_HC)) ==
            (result.steps[1].psw & (WORD0196_ZF|WORD0196_HC)));
    REQUIRE((result.steps[1].psw & WORD0196_CF) ==
            (initial.ram018e >= UINT8_C(128) ? WORD0196_CF : 0));
    REQUIRE(result.steps[2].a == result.steps[1].a);
    REQUIRE((result.steps[5].psw & WORD0196_ZF) == (word == 192 ? WORD0196_ZF : 0));
    REQUIRE((result.steps[5].psw & WORD0196_CF) == (below ? WORD0196_CF : 0));
    REQUIRE(result.steps[5].a == result.steps[4].a && result.steps[6].a == result.steps[5].a);
    REQUIRE(result.steps[6].psw == result.steps[5].psw);
    for (i = 0; i < result.write_count; ++i) {
        REQUIRE(result.writes[i].width_bits == 8);
        REQUIRE(result.writes[i].event_index == event && result.writes[i].write_ordinal == ordinal + i);
    }
    REQUIRE(result.writes[0].pc == 0x5572 && result.writes[0].address == 0x018E);
    REQUIRE(result.writes[0].old_value == initial.ram018e && result.writes[0].new_value == rotated);
    if (below) {
        REQUIRE(result.writes[1].pc == 0x55C1 && result.writes[1].address == 0x0117);
        REQUIRE(result.writes[1].old_value == initial.ram0117 && result.writes[1].new_value == 15);
        REQUIRE(result.writes[2].pc == 0x55C3 && result.writes[2].address == 0x018F);
        REQUIRE(result.writes[2].old_value == initial.ram018f && result.writes[2].new_value == 15);
    } else {
        REQUIRE(result.writes[1].pc == 0x557F && result.writes[1].address == 0x0109);
        REQUIRE(result.writes[1].old_value == initial.local[1] && result.writes[1].new_value == initial.ram0117);
        REQUIRE(result.writes[2].pc == 0x5582 && result.writes[2].address == 0x0117);
        REQUIRE(result.writes[2].old_value == initial.ram0117 && result.writes[2].new_value == expected.ram0117);
        if (!bypass) {
            REQUIRE(result.writes[3].pc == 0x558B && result.writes[3].address == 0x018F);
            REQUIRE(result.writes[3].old_value == initial.ram018f && result.writes[3].new_value == expected.ram018f);
            REQUIRE(result.writes[4].pc == 0x558E && result.writes[4].address == 0x012A);
            REQUIRE(result.writes[4].old_value == initial.ram012a && result.writes[4].new_value == expected.ram012a);
        }
    }
    *outgoing = actual;
    return true;
}

static word0196_state invented_state(void)
{
    word0196_state state = {0};
    unsigned i;
    state.a = UINT16_C(0xAB35); state.psw = UINT16_C(0x0DCB);
    state.pc = WORD0196_ENTRY_PC; state.lrb = UINT16_C(0x0021);
    state.x1 = UINT16_C(0x8123); state.x2 = UINT16_C(0xBEEF);
    state.dp = UINT16_C(0x2A42); state.usp = UINT16_C(0x0180); state.ssp = UINT16_C(0x07FE);
    state.sf = true;
    for (i = 0; i < 8; ++i) { state.local[i] = (uint8_t)(0xA5U + i); }
    state.ram0117 = UINT8_C(0xF3); state.ram0124 = UINT8_C(0xD2);
    state.ram0128 = UINT8_C(0x6D); state.ram012a = UINT8_C(0x36);
    state.ram018e = UINT8_C(0x8F); state.ram018f = UINT8_C(0xCB);
    state.ram0196[0] = UINT8_C(0xC0);
    return state;
}

static bool run_specs(void)
{
    const uint16_t words[] = {0,0xBF,0xC0,0xC1,0xFFFF};
    const uint8_t r0_values[] = {0,0xFF,0xA5,0x3C};
    unsigned w, byte, flags, gates, r;
    word0196_state state, outgoing;
    for (w = 0; w < sizeof(words)/sizeof(words[0]); ++w) {
        for (byte = 0; byte < 256; ++byte) {
            for (flags = 0; flags < 16; ++flags) {
                for (gates = 0; gates < 4; ++gates) {
                    for (r = 0; r < sizeof(r0_values)/sizeof(r0_values[0]); ++r) {
                        state = invented_state();
                        state.psw = (uint16_t)((state.psw & UINT16_C(0x0FFF)) | (uint16_t)(flags * 4096U));
                        state.ram0196[0] = (uint8_t)(words[w] % 256U);
                        state.ram0196[1] = (uint8_t)(words[w] / 256U);
                        state.ram018e = (uint8_t)byte;
                        state.local[0] = r0_values[r];
                        state.ram012a = (uint8_t)((state.ram012a & UINT8_C(0x7F)) | ((gates & 1U) != 0 ? 0x80U : 0U));
                        state.ram0124 = (uint8_t)((state.ram0124 & UINT8_C(0xDF)) | ((gates & 2U) != 0 ? 0x20U : 0U));
                        REQUIRE(check_vector(state, 23, 9, &outgoing));
                    }
                }
            }
        }
    }
    /* All word values separately check unsigned compare with distinctive LE input. */
    for (w = 0; w < 65536; ++w) {
        state = invented_state();
        state.ram0196[0] = (uint8_t)(w % 256U); state.ram0196[1] = (uint8_t)(w / 256U);
        REQUIRE(check_vector(state, 31, 2, &outgoing));
    }
    /* Every possible AH independently stays intact on every branch/gate. */
    for (byte = 0; byte < 256; ++byte) {
        for (w = 0; w < sizeof(words)/sizeof(words[0]); ++w) {
            for (gates = 0; gates < 4; ++gates) {
                state = invented_state();
                state.a = (uint16_t)((uint16_t)(byte * 256U) + UINT16_C(0x35));
                state.ram0196[0] = (uint8_t)(words[w] % 256U);
                state.ram0196[1] = (uint8_t)(words[w] / 256U);
                state.ram012a = (uint8_t)((state.ram012a & UINT8_C(0x7F)) | ((gates & 1U) != 0 ? 0x80U : 0U));
                state.ram0124 = (uint8_t)((state.ram0124 & UINT8_C(0xDF)) | ((gates & 2U) != 0 ? 0x20U : 0U));
                REQUIRE(check_vector(state, 47, 3, &outgoing));
            }
        }
    }
    /* Same-value writes still produce each separate ordered annotation. */
    state = invented_state(); state.ram018e = 0; state.ram0117 = 15; state.ram018f = 15;
    state.ram0196[0] = 0; state.ram0196[1] = 0;
    REQUIRE(check_vector(state, 80, 4, &outgoing));
    state = invented_state(); state.local[0] = 255; state.local[1] = 0;
    state.ram018e = 255; state.ram0117 = 0; state.ram018f = 0; state.ram012a = 1;
    state.ram0124 = 0;
    REQUIRE(check_vector(state, 85, 5, &outgoing));
    /* Persistent state, no RAM or A/flags repair between replay invocations.
     * PC re-entry is explicitly OFFLINE, not recovered scheduler/native execution. */
    for (w = 0; w < 5; ++w) {
        state = invented_state(); state.ram0196[0] = (uint8_t)(words[w] % 256U);
        state.ram0196[1] = (uint8_t)(words[w] / 256U);
        for (r = 0; r < 64; ++r) {
            state.pc = WORD0196_ENTRY_PC;
            REQUIRE(check_vector(state, 1000U + r * 5U, r, &outgoing));
            state = outgoing;
            ++checked_repeated;
        }
    }
    return true;
}

static bool negatives(void)
{
    word0196_state state = invented_state(), before;
    word0196_result result;
    word0196_replay_context context = {0,0};
    const uint16_t entries[] = {0,0x5501,0x5596,0x55C5,0x5533,0x55C8};
    const uint16_t contexts[] = {0,0x20,0x22,0x41,0xFFFF};
    unsigned i;
    for (i = 0; i < sizeof(entries)/sizeof(entries[0]); ++i) {
        state = invented_state(); state.pc = entries[i]; before = state;
        REQUIRE(word0196_replay(&state,&context,&result) == WORD0196_UNSUPPORTED_ENTRY);
        REQUIRE(state_equal(&state,&before)); ++checked_negative;
    }
    for (i = 0; i < sizeof(contexts)/sizeof(contexts[0]); ++i) {
        state = invented_state(); state.lrb = contexts[i]; before = state;
        REQUIRE(word0196_replay(&state,&context,&result) == WORD0196_UNKNOWN_MEMORY_CONTEXT);
        REQUIRE(state_equal(&state,&before)); ++checked_negative;
    }
    state = invented_state(); state.halted = true; before = state;
    REQUIRE(word0196_replay(&state,&context,&result) == WORD0196_HALTED_INPUT);
    REQUIRE(state_equal(&state,&before)); ++checked_negative;
    state = invented_state(); before = state; context.write_ordinal_base = UINT32_MAX;
    REQUIRE(word0196_replay(&state,&context,&result) == WORD0196_ORDINAL_OVERFLOW);
    REQUIRE(state_equal(&state,&before)); ++checked_negative;
    REQUIRE(word0196_replay(NULL,&context,&result) == WORD0196_INVALID_ARGUMENT); ++checked_negative;
    REQUIRE(word0196_replay(&state,NULL,&result) == WORD0196_INVALID_ARGUMENT); ++checked_negative;
    REQUIRE(word0196_replay(&state,&context,NULL) == WORD0196_INVALID_ARGUMENT); ++checked_negative;
    return true;
}

int main(void)
{
    if (!run_specs() || !negatives()) { return 1; }
    printf("{\"suite\":\"word0196-independent-primary-specification\","
           "\"inventedVectors\":%u,\"repeatedCallsIncluded\":%u,\"negativeCases\":%u,"
           "\"failures\":0,\"actualRomExecutions\":0}\n",
           (unsigned)checked_vectors, (unsigned)checked_repeated, (unsigned)checked_negative);
    return 0;
}
