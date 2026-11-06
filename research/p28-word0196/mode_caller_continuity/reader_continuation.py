"""Two distinct reviewed continuations; neither BRK nor IE write is modeled."""


def continue_reader(effects, boundary):
    if boundary == 0x3FB1:
        effects.store(0x3FB1, 0xF5, [0x50], 'ImmediateStore', 'Literal')
        effects.step(0x3FB1, 0x3FB5)
        return effects.finish('FailureDiagnosticPrepared', 0x3FB5)
    if boundary == 0x3FF7:
        effects.load_word(0x3FF7, 0x3FF9, address=0xFA)
        return effects.finish('ReaderAcceptedBeforeIeWrite', 0x3FF9)
    raise ValueError('ReviewedReaderContinuationRequired')
